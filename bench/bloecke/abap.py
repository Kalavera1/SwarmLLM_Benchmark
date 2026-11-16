"""Block abap: Wie gut schreibt das Modell ABAP? (7 Aufgaben wie im B300-Test)

Bewertung ohne SAP-System, in zwei Teilen:
  Kriterien   feste Liste je Aufgabe (bench/daten/abap_aufgaben.json): erwartete
              Bestandteile als regulärer Ausdruck; „verboten“ = darf im Code
              nicht vorkommen (z. B. MOVE bei der Modernisierung)
  abaplint    Syntaxprüfung der Codeblöcke (Regeln parser_error und
              cds_parser_error), sofern npx verfügbar ist. Ohne npx wird nur
              nach Kriterien bewertet und das im Ergebnis vermerkt.
abaplint prüft keine Tabellen oder Klassen aus dem Data Dictionary (kein SAP-
System), sondern nur, ob die Anweisungen syntaktisch gültig sind.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

EBENE = "Abnahme"
BESCHREIBUNG = "7 ABAP-Aufgaben, Kriterienliste und abaplint-Syntaxprüfung"

AUFGABEN_DATEI = Path(__file__).resolve().parent.parent / "daten" / "abap_aufgaben.json"
ABAPLINT_VERSION = "2.120.107"  # gepinnt (Regel 4); Stand npm 16.11.2026
DATEIENDUNG = {"prog": ".prog.abap", "clas": ".clas.abap", "ddls": ".ddls.asddls"}
CODEBLOCK = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)
ABAPLINT_KONFIG = {
    "global": {"files": "/src/**/*.*"},
    "syntax": {"version": "v757", "errorNamespace": "."},
    "rules": {"parser_error": True, "cds_parser_error": True},
}


# ---------------------------------------------------------------------------
# Hilfen: Aufgaben laden, Code herausziehen
# ---------------------------------------------------------------------------
def lade_aufgaben() -> list[dict]:
    return json.loads(AUFGABEN_DATEI.read_text(encoding="utf-8"))["aufgaben"]


def codebloecke(text: str) -> str:
    return "\n".join(block.strip() for block in CODEBLOCK.findall(text))


# ---------------------------------------------------------------------------
# Kriterien prüfen
# Erwartete Muster gelten für die ganze Antwort (Erklärung zählt mit, wichtig
# für die Fehlersuche); verbotene nur für den Code.
# ---------------------------------------------------------------------------
def pruefe_kriterien(aufgabe: dict, antwort: str, code: str) -> list[dict]:
    ergebnisse = []
    for k in aufgabe["kriterien"]:
        if k.get("verboten"):
            erfuellt = bool(code) and not re.search(k["muster"], code, re.I)
        else:
            erfuellt = bool(re.search(k["muster"], antwort, re.I))
        ergebnisse.append({"beschreibung": k["beschreibung"], "erfuellt": erfuellt})
    return ergebnisse


# ---------------------------------------------------------------------------
# abaplint: Syntaxprüfung über npx (lädt das Paket beim ersten Aufruf)
# Liefert None, wenn abaplint nicht verfügbar ist.
# ---------------------------------------------------------------------------
def abaplint_verfuegbar() -> bool:
    return shutil.which("npx") is not None


def abaplint(code: str, dateityp: str, name: str) -> dict | None:
    if dateityp not in DATEIENDUNG or not code or not abaplint_verfuegbar():
        return None
    with tempfile.TemporaryDirectory() as ordner:
        basis = Path(ordner)
        (basis / "src").mkdir()
        (basis / "src" / f"zbench_{name}{DATEIENDUNG[dateityp]}").write_text(code + "\n", encoding="utf-8")
        (basis / "abaplint.json").write_text(json.dumps(ABAPLINT_KONFIG), encoding="utf-8")
        try:
            lauf = subprocess.run(
                ["npx", "--yes", f"@abaplint/cli@{ABAPLINT_VERSION}", "abaplint.json", "--format", "json"],
                cwd=basis,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as fehler:
            return {"fehler": str(fehler)}
    json_zeile = next((z for z in reversed(lauf.stdout.splitlines()) if z.startswith("[")), "[]")
    try:
        befunde = json.loads(json_zeile)
    except json.JSONDecodeError:
        return {"fehler": lauf.stdout[-300:] + lauf.stderr[-300:]}
    return {
        "syntaxfehler": len(befunde),
        "befunde": [f"Zeile {b['start']['row']}: {b['description']}" for b in befunde[:10]],
    }


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    ergebnisse = []
    for aufgabe in lade_aufgaben():
        antwort = ctx.client.chat([{"role": "user", "content": aufgabe["prompt"]}], max_tokens=32768)
        ctx.merke("abap", antwort, aufgabe=aufgabe["id"])
        code = codebloecke(antwort.inhalt)
        kriterien = pruefe_kriterien(aufgabe, antwort.inhalt, code)
        lint = abaplint(code, aufgabe["dateityp"], aufgabe["id"]) if antwort.ok else None
        erfuellt = sum(k["erfuellt"] for k in kriterien)
        syntax = "-" if lint is None else lint.get("syntaxfehler", "Fehler")
        ctx.log(
            f"{aufgabe['id']:<15} Kriterien {erfuellt}/{len(kriterien)}, Syntaxfehler: {syntax}, {antwort.dauer:.0f} s"
        )
        ergebnisse.append(
            {
                "id": aufgabe["id"],
                "titel": aufgabe["titel"],
                "kriterien_erfuellt": erfuellt,
                "kriterien_gesamt": len(kriterien),
                "kriterien": kriterien,
                "abaplint": lint,
                "denk_tokens": antwort.reasoning_tokens,
                "dauer_s": round(antwort.dauer, 1),
                "fehler": antwort.fehler[:200] or None,
            }
        )

    erfuellt = sum(e["kriterien_erfuellt"] for e in ergebnisse)
    gesamt = sum(e["kriterien_gesamt"] for e in ergebnisse)
    syntaxfehler = [
        e["abaplint"]["syntaxfehler"] for e in ergebnisse if e["abaplint"] and "syntaxfehler" in e["abaplint"]
    ]
    return {
        "bestanden": None,  # Qualitätsmaß zum Vergleichen, keine harte Grenze
        "kennzahlen": {
            "kriterien_quote": round(erfuellt / gesamt, 3) if gesamt else None,
            "aufgaben_ohne_syntaxfehler": sum(1 for s in syntaxfehler if s == 0),
            "aufgaben_mit_syntaxpruefung": len(syntaxfehler),
            "abaplint": f"@abaplint/cli@{ABAPLINT_VERSION}" if abaplint_verfuegbar() else "nicht verfügbar (kein npx)",
        },
        "aufgaben": ergebnisse,
    }
