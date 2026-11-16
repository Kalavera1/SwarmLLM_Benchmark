"""HTTP-Client für die OpenAI-kompatible API mit Zeitmessung pro Token.

Misst bei gestreamten Antworten:
  ttft          Zeit bis zum ersten Token (Inhalt oder Denken) in Sekunden
  dauer         Zeit bis zum Ende der Antwort
  itl           Abstände zwischen den Stücken (inter-token latency)
Dazu Inhalt, Denk-Text, Tool-Calls und die Token-Zahlen aus `usage`.

Nur Standardbibliothek (http.client), damit kein requests/httpx nötig ist.
Eigener User-Agent: Der RunPod-Proxy blockt `Python-urllib` (Erfahrung B300).
"""

from __future__ import annotations

import http.client
import json
import ssl
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from bench import VERSION

USER_AGENT = f"SwarmLLM_Benchmark/{VERSION}"
STANDARD_TIMEOUT = 1800  # Sekunden; ein kalter 1M-Prompt braucht mehrere Minuten


# ---------------------------------------------------------------------------
# Ergebnis einer Anfrage
# ---------------------------------------------------------------------------
@dataclass
class Antwort:
    ok: bool = False
    status: int = 0
    fehler: str = ""
    start: float = 0.0  # time.monotonic() beim Absenden, für Lastauswertung
    ttft: float | None = None
    dauer: float = 0.0
    itl: list[float] = field(default_factory=list)
    inhalt: str = ""
    denken: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    stuecke: int = 0

    @property
    def ausgabe_tokens(self) -> int:
        """Erzeugte Tokens; ohne usage-Angabe ersatzweise die Zahl der Stücke."""
        return self.completion_tokens if self.completion_tokens is not None else self.stuecke

    @property
    def decode_tok_s(self) -> float | None:
        """Ausgabetempo nach dem ersten Token, aus Sicht eines Nutzers."""
        if self.ttft is None or self.ausgabe_tokens < 2 or self.dauer <= self.ttft:
            return None
        return (self.ausgabe_tokens - 1) / (self.dauer - self.ttft)

    @property
    def tpot(self) -> float | None:
        """Zeit pro Ausgabetoken nach dem ersten (time per output token)."""
        tempo = self.decode_tok_s
        return 1 / tempo if tempo else None

    def kurz(self) -> dict:
        """Kompakte Form für die Rohdaten (ohne lange Texte)."""
        return {
            "ok": self.ok,
            "status": self.status,
            "fehler": self.fehler[:300],
            "ttft": self.ttft,
            "dauer": round(self.dauer, 4),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "decode_tok_s": self.decode_tok_s,
            "finish_reason": self.finish_reason,
        }


# ---------------------------------------------------------------------------
# Client
# Eine Instanz pro Messziel; thread-sicher, weil jede Anfrage eine eigene
# Verbindung öffnet (wichtig für die Lasttests mit vielen Threads).
# ---------------------------------------------------------------------------
class Client:
    def __init__(self, basis_url: str, api_key: str, modell: str, timeout: float = STANDARD_TIMEOUT):
        self.basis_url = basis_url.rstrip("/")
        self.api_key = api_key
        self.modell = modell
        self.timeout = timeout

    # --- Verbindung und Header ------------------------------------------
    def _verbindung(self, url: str, timeout: float) -> tuple[http.client.HTTPConnection, str]:
        teile = urlsplit(url)
        pfad = teile.path or "/"
        if teile.query:
            pfad += "?" + teile.query
        if teile.scheme == "https":
            return http.client.HTTPSConnection(
                teile.netloc, timeout=timeout, context=ssl.create_default_context()
            ), pfad
        return http.client.HTTPConnection(teile.netloc, timeout=timeout), pfad

    def _header(self, mit_key: bool = True) -> dict[str, str]:
        header = {"User-Agent": USER_AGENT, "Content-Type": "application/json", "Accept": "application/json"}
        if mit_key and self.api_key:
            header["Authorization"] = f"Bearer {self.api_key}"
        return header

    # --- Einfache Anfragen ------------------------------------------------
    def anfrage(
        self, methode: str, url: str, daten: dict | None = None, mit_key: bool = True, timeout: float = 30
    ) -> tuple[int, bytes]:
        """Rohe Anfrage; liefert (Status, Antwortkörper). Netzfehler -> Status 0."""
        verbindung, pfad = self._verbindung(url, timeout)
        try:
            koerper = json.dumps(daten).encode() if daten is not None else None
            verbindung.request(methode, pfad, body=koerper, headers=self._header(mit_key))
            antwort = verbindung.getresponse()
            return antwort.status, antwort.read()
        except (OSError, http.client.HTTPException) as fehler:
            return 0, str(fehler).encode()
        finally:
            verbindung.close()

    def get_json(self, pfad: str, mit_key: bool = True) -> tuple[int, dict]:
        status, roh = self.anfrage("GET", self.basis_url + pfad, mit_key=mit_key)
        try:
            return status, json.loads(roh or b"{}")
        except json.JSONDecodeError:
            return status, {}

    # --- Chat-Anfrage mit Zeitmessung ------------------------------------
    def chat(
        self,
        nachrichten: list[dict],
        max_tokens: int = 512,
        stream: bool = True,
        tools: list[dict] | None = None,
        extra: dict | None = None,
        temperature: float | None = 0.0,
        timeout: float | None = None,
    ) -> Antwort:
        daten: dict = {"model": self.modell, "messages": nachrichten, "max_tokens": max_tokens, "stream": stream}
        if temperature is not None:
            daten["temperature"] = temperature
        if stream:
            daten["stream_options"] = {"include_usage": True}
        if tools:
            daten["tools"] = tools
        if extra:
            daten.update(extra)

        antwort = Antwort(start=time.monotonic())
        verbindung, pfad = self._verbindung(self.basis_url + "/chat/completions", timeout or self.timeout)
        try:
            verbindung.request("POST", pfad, body=json.dumps(daten).encode(), headers=self._header())
            roh = verbindung.getresponse()
            antwort.status = roh.status
            if roh.status != 200:
                antwort.fehler = roh.read().decode(errors="replace")[:1000]
            elif stream:
                self._lies_stream(roh, antwort)
            else:
                self._lies_komplett(json.loads(roh.read()), antwort)
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as fehler:
            antwort.fehler = f"{type(fehler).__name__}: {fehler}"
        finally:
            verbindung.close()
        antwort.dauer = time.monotonic() - antwort.start
        antwort.ok = antwort.status == 200 and not antwort.fehler
        return antwort

    # --- Antworten auswerten ---------------------------------------------
    @staticmethod
    def _usage(usage: dict | None, antwort: Antwort) -> None:
        if not usage:
            return
        antwort.prompt_tokens = usage.get("prompt_tokens")
        antwort.completion_tokens = usage.get("completion_tokens")
        details = usage.get("completion_tokens_details") or {}
        if details.get("reasoning_tokens") is not None:
            antwort.reasoning_tokens = details["reasoning_tokens"]

    def _lies_komplett(self, daten: dict, antwort: Antwort) -> None:
        wahl = (daten.get("choices") or [{}])[0]
        nachricht = wahl.get("message") or {}
        antwort.inhalt = nachricht.get("content") or ""
        # vLLM liefert den Denk-Text je nach Version als reasoning_content oder reasoning
        antwort.denken = nachricht.get("reasoning_content") or nachricht.get("reasoning") or ""
        antwort.tool_calls = nachricht.get("tool_calls") or []
        antwort.finish_reason = wahl.get("finish_reason")
        antwort.ttft = time.monotonic() - antwort.start
        self._usage(daten.get("usage"), antwort)

    def _lies_stream(self, roh: http.client.HTTPResponse, antwort: Antwort) -> None:
        inhalt: list[str] = []
        denken: list[str] = []
        tools: dict[int, dict] = {}
        letztes: float | None = None
        for zeile_roh in roh:
            zeile = zeile_roh.decode("utf-8", errors="replace").strip()
            if not zeile.startswith("data:"):
                continue
            nutzlast = zeile[5:].strip()
            if nutzlast == "[DONE]":
                break
            try:
                stueck = json.loads(nutzlast)
            except json.JSONDecodeError:
                continue
            self._usage(stueck.get("usage"), antwort)
            for wahl in stueck.get("choices") or []:
                delta = wahl.get("delta") or {}
                neu = False
                if delta.get("content"):
                    inhalt.append(delta["content"])
                    neu = True
                text = delta.get("reasoning_content") or delta.get("reasoning")
                if text:
                    denken.append(text)
                    neu = True
                for tc in delta.get("tool_calls") or []:
                    eintrag = tools.setdefault(
                        tc.get("index", 0), {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                    )
                    eintrag["id"] = tc.get("id") or eintrag["id"]
                    funktion = tc.get("function") or {}
                    eintrag["function"]["name"] += funktion.get("name") or ""
                    eintrag["function"]["arguments"] += funktion.get("arguments") or ""
                    neu = True
                if wahl.get("finish_reason"):
                    antwort.finish_reason = wahl["finish_reason"]
                if neu:
                    jetzt = time.monotonic()
                    if antwort.ttft is None:
                        antwort.ttft = jetzt - antwort.start
                    elif letztes is not None:
                        antwort.itl.append(jetzt - letztes)
                    letztes = jetzt
                    antwort.stuecke += 1
        antwort.inhalt = "".join(inhalt)
        antwort.denken = "".join(denken)
        antwort.tool_calls = [tools[i] for i in sorted(tools)]

    # --- vLLM-spezifische Endpunkte (beim Mock nicht vorhanden) -----------
    def tokens_zaehlen(self, text: str) -> int | None:
        """Exakte Token-Zahl über /tokenize von vLLM; None, wenn nicht verfügbar."""
        server = self.basis_url[: -len("/v1")] if self.basis_url.endswith("/v1") else self.basis_url
        status, roh = self.anfrage("POST", server + "/tokenize", {"model": self.modell, "prompt": text}, timeout=120)
        if status != 200:
            return None
        try:
            return int(json.loads(roh).get("count"))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def metriken(self) -> dict[str, float]:
        """Zähler aus /metrics (Prometheus-Format), über alle Labels summiert.

        Nur Zeilen mit dem Präfix "vllm:" werden gelesen. Leeres Ergebnis, wenn der
        Server keine Metriken anbietet (Mock, LiteLLM).
        """
        server = self.basis_url[: -len("/v1")] if self.basis_url.endswith("/v1") else self.basis_url
        status, roh = self.anfrage("GET", server + "/metrics", timeout=30)
        if status != 200:
            return {}
        return parse_prometheus(roh.decode("utf-8", errors="replace"))


# ---------------------------------------------------------------------------
# Prometheus-Textformat lesen
# Zeilen wie: vllm:prompt_tokens_total{model_name="x"} 1234.0
# Werte gleichen Namens (verschiedene Labels) werden addiert.
# ---------------------------------------------------------------------------
def parse_prometheus(text: str) -> dict[str, float]:
    werte: dict[str, float] = {}
    for zeile in text.splitlines():
        if not zeile.startswith("vllm:"):
            continue
        name_teil, _, wert_teil = zeile.rpartition(" ")
        name = name_teil.split("{", 1)[0].strip()
        try:
            werte[name] = werte.get(name, 0.0) + float(wert_teil)
        except ValueError:
            continue
    return werte
