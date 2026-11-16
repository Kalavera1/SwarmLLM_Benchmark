"""Block integration: Funktioniert die Kette bis zum Modell?

Prüft ohne Lastmessung:
  modell_geladen      der erwartete Modellname steht in /v1/models (nicht das
                      vLLM-Standardmodell – Stolperstein aus dem B300-Test)
  key_schutz          eine Anfrage ohne Key wird abgewiesen (Regel 8)
  chat                einfache Antwort ohne Streaming
  streaming           gestreamte Antwort mit erstem Token und Abschluss
  usage               der Server meldet Token-Zahlen
  tool_call           Tool-Call im OpenAI-Format mit gültigem JSON
  kontext_fuer_agent  mindestens 64k Kontext (Mindestwert von Hermes Agent)
"""

from __future__ import annotations

import json

EBENE = "Integration"
BESCHREIBUNG = "Modellname, Key-Schutz, Streaming, Tool-Calls, Kontext für Agenten"
MIN_KONTEXT_AGENT = 65536

WETTER_TOOL = {
    "type": "function",
    "function": {
        "name": "wetter_abfragen",
        "description": "Liefert das aktuelle Wetter für eine Stadt.",
        "parameters": {
            "type": "object",
            "properties": {"stadt": {"type": "string", "description": "Name der Stadt"}},
            "required": ["stadt"],
        },
    },
}


# ---------------------------------------------------------------------------
# Einzelprüfungen; jede liefert (bestanden, Detailtext)
# ---------------------------------------------------------------------------
def pruefe_modell(ctx) -> tuple[bool, str]:
    status, daten = ctx.client.get_json("/models")
    namen = [m.get("id") for m in daten.get("data", [])]
    return ctx.client.modell in namen, f"HTTP {status}, angeboten: {namen}"


def pruefe_key_schutz(ctx) -> tuple[bool, str]:
    if not ctx.profil.key_pflicht:
        return True, "Profil erlaubt Betrieb ohne Key (nur Mock)"
    if not ctx.client.api_key:
        return False, "kein Key konfiguriert – Endpunkt wäre offen"
    status, _ = ctx.client.get_json("/models", mit_key=False)
    return not (200 <= status < 300), f"ohne Key: HTTP {status}"


def pruefe_chat(ctx) -> tuple[bool, str]:
    antwort = ctx.client.chat(
        [{"role": "user", "content": "Antworte mit genau einem Wort: Hallo"}],
        max_tokens=1024,
        stream=False,
        extra=ctx.denk_extra(),
    )
    ctx.merke("chat", antwort)
    return antwort.ok and bool(antwort.inhalt.strip()), f"HTTP {antwort.status}, Inhalt: {antwort.inhalt[:60]!r}"


def pruefe_streaming(ctx) -> tuple[bool, str, object]:
    antwort = ctx.client.chat(
        [{"role": "user", "content": "Zähle von eins bis fünf."}], max_tokens=1024, extra=ctx.denk_extra()
    )
    ctx.merke("streaming", antwort)
    ok = antwort.ok and antwort.ttft is not None and antwort.finish_reason is not None
    return ok, f"erstes Token nach {antwort.ttft}, Ende: {antwort.finish_reason}", antwort


def pruefe_tool_call(ctx) -> tuple[bool, str]:
    antwort = ctx.client.chat(
        [{"role": "user", "content": "Nutze das Tool wetter_abfragen, um das Wetter in Berlin abzufragen."}],
        max_tokens=4096,
        tools=[WETTER_TOOL],
    )
    ctx.merke("tool_call", antwort)
    if not antwort.tool_calls:
        return False, f"kein Tool-Call; Inhalt: {antwort.inhalt[:80]!r}"
    aufruf = antwort.tool_calls[0]["function"]
    try:
        argumente = json.loads(aufruf.get("arguments") or "{}")
    except json.JSONDecodeError:
        return False, f"Argumente kein gültiges JSON: {aufruf.get('arguments')!r}"
    ok = aufruf.get("name") == "wetter_abfragen" and isinstance(argumente, dict)
    return ok, f"{aufruf.get('name')}({argumente})"


def pruefe_kontext(ctx) -> tuple[bool, str]:
    laenge = ctx.max_kontext()
    return laenge >= MIN_KONTEXT_AGENT, f"{laenge} Tokens"


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    pruefungen: dict[str, dict] = {}

    def eintragen(name: str, ok: bool, detail: str) -> None:
        pruefungen[name] = {"bestanden": ok, "detail": detail}
        ctx.log(f"{'ok    ' if ok else 'FEHLER'} {name}: {detail}")

    eintragen("modell_geladen", *pruefe_modell(ctx))
    eintragen("key_schutz", *pruefe_key_schutz(ctx))
    eintragen("chat", *pruefe_chat(ctx))
    ok, detail, antwort = pruefe_streaming(ctx)
    eintragen("streaming", ok, detail)
    eintragen("usage", antwort.prompt_tokens is not None, f"prompt_tokens={antwort.prompt_tokens}")
    eintragen("tool_call", *pruefe_tool_call(ctx))
    eintragen("kontext_fuer_agent", *pruefe_kontext(ctx))

    return {"bestanden": all(p["bestanden"] for p in pruefungen.values()), "pruefungen": pruefungen}
