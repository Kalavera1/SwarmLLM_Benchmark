#!/usr/bin/env python3
"""Mock-Server, der die OpenAI-API von vLLM nachahmt – ohne GPU.

Zweck: LiteLLM, OpenWebUI und die Testsuite lassen sich damit testen, bevor
ein teurer GPU-Pod läuft. Nur Standardbibliothek, damit er in jedem Image mit
Python 3.10+ läuft.

Endpunkte:
  GET  /health                 -> 200, immer ohne Key (für Healthchecks)
  GET  /v1/models              -> Liste mit dem Mock-Modell
  POST /v1/chat/completions    -> Antwort, wahlweise gestreamt (SSE)

Verhalten über Umgebungsvariablen:
  MOCK_API_KEY         Wenn gesetzt: Anfragen ohne passenden Bearer-Key -> 401
                       (wie vLLM mit VLLM_API_KEY, Regel 8)
  MOCK_API_KEY_FILE    Alternativ: Datei mit dem Key, z. B. ein Docker Secret
  MOCK_MODEL           Modellname (Standard: mock-model)
  MOCK_PREFILL_TOK_S   simulierte Einlese-Geschwindigkeit (Standard: 20000)
  MOCK_DECODE_TOK_S    simulierte Ausgabe-Geschwindigkeit (Standard: 200)
  MOCK_OUTPUT_TOKENS   Länge der Antwort in Tokens (Standard: 32)
  MOCK_REASONING       "1": Antwort enthält zusätzlich reasoning_content

Tool-Calls: Enthält die Anfrage `tools` und die letzte Nutzernachricht das Wort
"tool", antwortet der Mock mit einem Aufruf des ersten Tools.

Aufruf: python3 mock_openai.py [--host 0.0.0.0] [--port 8000]
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def lies_api_key() -> str:
    """Key aus MOCK_API_KEY oder aus der Datei in MOCK_API_KEY_FILE (Docker Secret)."""
    datei = os.environ.get("MOCK_API_KEY_FILE", "")
    if datei and os.path.isfile(datei):
        with open(datei, encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("MOCK_API_KEY", "")


MODELL = os.environ.get("MOCK_MODEL", "mock-model")
API_KEY = lies_api_key()
PREFILL_TOK_S = float(os.environ.get("MOCK_PREFILL_TOK_S", "20000"))
DECODE_TOK_S = float(os.environ.get("MOCK_DECODE_TOK_S", "200"))
AUSGABE_TOKENS = int(os.environ.get("MOCK_OUTPUT_TOKENS", "32"))
MIT_DENKEN = os.environ.get("MOCK_REASONING", "") == "1"

WOERTER = ["Das", "ist", "eine", "Antwort", "des", "Mock-Servers", "ohne", "GPU"]


def schaetze_tokens(text: str) -> int:
    """Grobe Schätzung wie bei vielen Tokenizern: etwa 4 Zeichen pro Token."""
    return max(1, len(text) // 4)


def prompt_text(nachrichten: list[dict]) -> str:
    teile = []
    for n in nachrichten:
        inhalt = n.get("content") or ""
        if isinstance(inhalt, list):  # multimodal: nur Textteile zählen
            inhalt = " ".join(t.get("text", "") for t in inhalt if isinstance(t, dict))
        teile.append(str(inhalt))
    return "\n".join(teile)


def antwort_tokens(anzahl: int) -> list[str]:
    return [WOERTER[i % len(WOERTER)] + " " for i in range(anzahl)]


def soll_tool_rufen(anfrage: dict) -> bool:
    if not anfrage.get("tools"):
        return False
    nutzer = [n for n in anfrage.get("messages", []) if n.get("role") == "user"]
    return bool(nutzer) and "tool" in prompt_text(nutzer[-1:]).lower()


class Handler(BaseHTTPRequestHandler):
    server_version = "MockOpenAI/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # kompakte Logs
        print(f"{self.address_string()} {fmt % args}", flush=True)

    # --- Hilfen -----------------------------------------------------------
    def _json(self, status: int, daten: dict) -> None:
        roh = json.dumps(daten).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(roh)))
        self.end_headers()
        self.wfile.write(roh)

    def _fehler(self, status: HTTPStatus, text: str) -> None:
        self._json(status, {"error": {"message": text, "type": status.phrase, "code": status.value}})

    def _autorisiert(self) -> bool:
        if not API_KEY:
            return True
        if self.headers.get("Authorization", "") == f"Bearer {API_KEY}":
            return True
        self._fehler(HTTPStatus.UNAUTHORIZED, "Ungültiger oder fehlender API-Key")
        return False

    # --- Endpunkte --------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 (Name von BaseHTTPRequestHandler vorgegeben)
        if self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok"})
        elif self.path == "/v1/models":
            if self._autorisiert():
                self._json(
                    HTTPStatus.OK,
                    {"object": "list", "data": [{"id": MODELL, "object": "model", "owned_by": "mock"}]},
                )
        else:
            self._fehler(HTTPStatus.NOT_FOUND, f"Unbekannter Pfad: {self.path}")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self._fehler(HTTPStatus.NOT_FOUND, f"Unbekannter Pfad: {self.path}")
            return
        if not self._autorisiert():
            return
        try:
            laenge = int(self.headers.get("Content-Length", "0"))
            anfrage = json.loads(self.rfile.read(laenge) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._fehler(HTTPStatus.BAD_REQUEST, "Kein gültiges JSON")
            return
        if not isinstance(anfrage.get("messages"), list) or not anfrage["messages"]:
            self._fehler(HTTPStatus.BAD_REQUEST, "Feld 'messages' fehlt oder ist leer")
            return

        prompt_tokens = schaetze_tokens(prompt_text(anfrage["messages"]))
        max_tokens = anfrage.get("max_tokens") or anfrage.get("max_completion_tokens") or AUSGABE_TOKENS
        tokens = antwort_tokens(min(AUSGABE_TOKENS, int(max_tokens)))
        time.sleep(prompt_tokens / PREFILL_TOK_S)  # simuliertes Einlesen

        if anfrage.get("stream"):
            self._stream(anfrage, prompt_tokens, tokens)
        else:
            self._komplett(anfrage, prompt_tokens, tokens)

    # --- Antwortformen ----------------------------------------------------
    def _basis(self) -> dict:
        return {"id": f"chatcmpl-{uuid.uuid4().hex[:24]}", "created": int(time.time()), "model": MODELL}

    def _tool_call(self, anfrage: dict) -> dict:
        name = anfrage["tools"][0].get("function", {}).get("name", "unbekannt")
        return {
            "id": f"call_{uuid.uuid4().hex[:12]}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps({"mock": True})},
        }

    def _komplett(self, anfrage: dict, prompt_tokens: int, tokens: list[str]) -> None:
        time.sleep(len(tokens) / DECODE_TOK_S)
        nachricht: dict = {"role": "assistant", "content": "".join(tokens).strip()}
        grund = "stop"
        if soll_tool_rufen(anfrage):
            nachricht = {"role": "assistant", "content": None, "tool_calls": [self._tool_call(anfrage)]}
            grund = "tool_calls"
        elif MIT_DENKEN:
            nachricht["reasoning_content"] = "Mock denkt kurz nach."
        self._json(
            HTTPStatus.OK,
            {
                **self._basis(),
                "object": "chat.completion",
                "choices": [{"index": 0, "message": nachricht, "finish_reason": grund}],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": len(tokens),
                    "total_tokens": prompt_tokens + len(tokens),
                },
            },
        )

    def _sende_chunk(self, daten: dict | str) -> None:
        roh = daten if isinstance(daten, str) else json.dumps(daten)
        zeile = f"data: {roh}\n\n".encode()
        self.wfile.write(f"{len(zeile):x}\r\n".encode() + zeile + b"\r\n")
        self.wfile.flush()

    def _stream(self, anfrage: dict, prompt_tokens: int, tokens: list[str]) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        basis = {**self._basis(), "object": "chat.completion.chunk"}

        def chunk(delta: dict, grund: str | None = None) -> dict:
            return {**basis, "choices": [{"index": 0, "delta": delta, "finish_reason": grund}]}

        self._sende_chunk(chunk({"role": "assistant", "content": ""}))
        if soll_tool_rufen(anfrage):
            self._sende_chunk(chunk({"tool_calls": [{"index": 0, **self._tool_call(anfrage)}]}))
            grund, ausgegeben = "tool_calls", 1
        else:
            if MIT_DENKEN:
                self._sende_chunk(chunk({"reasoning_content": "Mock denkt kurz nach."}))
            for t in tokens:
                time.sleep(1 / DECODE_TOK_S)
                self._sende_chunk(chunk({"content": t}))
            grund, ausgegeben = "stop", len(tokens)
        self._sende_chunk(chunk({}, grund))
        if (anfrage.get("stream_options") or {}).get("include_usage"):
            self._sende_chunk(
                {
                    **basis,
                    "choices": [],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": ausgegeben,
                        "total_tokens": prompt_tokens + ausgegeben,
                    },
                }
            )
        self._sende_chunk("[DONE]")
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="0.0.0.0")  # noqa: S104 (im Container gewollt, nur im Overlay-Netz erreichbar)
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    schutz = "mit API-Key" if API_KEY else "OHNE API-Key"
    print(f"Mock-Server {MODELL} auf {args.host}:{args.port} ({schutz})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
