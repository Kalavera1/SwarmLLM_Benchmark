"""Block agent: Taugt das Modell als Arbeitsmodell für einen Agenten (Hermes)?

Eine echte Agentenschleife mit Tools, die lokal ausgeführt werden:
  datei_lesen(pfad)     liefert Inhalte aus einem festen, ausgedachten Dateisystem
  rechnen(ausdruck)     rechnet sicher (nur Zahlen und + - * / ( ) .)
Jede Aufgabe braucht mehrere Tool-Aufrufe und hat ein eindeutiges Ergebnis.

Wie bei Hermes steht vorher eine lange Projektdokumentation im Kontext
(schnell 20k, voll 60k Tokens), damit die Schleife unter realistischer
Kontextlänge läuft. Gemessen: Erfolgsquote, gültige Tool-Calls, Runden, Zeit.
"""

from __future__ import annotations

import ast
import json
import operator

from bench import statistik, texte
from bench.ablauf import parallel
from bench.zahlen import ergebnis_lesen

EBENE = "Abnahme"
BESCHREIBUNG = "Agentenschleife mit Tools und langer Dokumentation im Kontext"

MAX_RUNDEN = 10
DOKU_TOKENS = {"schnell": 20_000, "voll": 60_000}
WIEDERHOLUNGEN = {"schnell": 1, "voll": 2}
GLEICHZEITIG = {"schnell": 1, "voll": 4}

# ---------------------------------------------------------------------------
# Ausgedachtes Dateisystem und Aufgaben mit fester Lösung
# ---------------------------------------------------------------------------
DATEIEN = {
    "lager/nord.txt": "Artikel A-17: 140 Stück\nArtikel B-02: 55 Stück\nArtikel C-33: 12 Stück",
    "lager/sued.txt": "Artikel A-17: 86 Stück\nArtikel B-02: 210 Stück\nArtikel D-41: 7 Stück",
    "preise.csv": "artikel;preis_eur\nA-17;12.50\nB-02;3.20\nC-33;199.00\nD-41;48.75",
    "team/schichten.txt": (
        "Frühschicht: 6 Personen à 7,5 Stunden\n"
        "Spätschicht: 4 Personen à 7,5 Stunden\n"
        "Nachtschicht: 2 Personen à 8 Stunden"
    ),
    "team/stundensatz.txt": "Stundensatz: 31,40 EUR",
}

AUFGABEN = [
    {
        "text": "Lies lager/nord.txt und lager/sued.txt. Addiere den Bestand von Artikel A-17 aus beiden Lagern "
        "und berechne den Gesamtwert mit dem Preis aus preise.csv.",
        "ergebnis": 2825.0,  # (140 + 86) * 12.50
    },
    {
        "text": "Berechne den Lagerwert von Artikel B-02 über beide Lager (lager/nord.txt, lager/sued.txt) "
        "mit dem Preis aus preise.csv.",
        "ergebnis": 848.0,  # (55 + 210) * 3.20
    },
    {
        "text": "Berechne die Personalkosten eines Tages: Lies team/schichten.txt und team/stundensatz.txt, "
        "multipliziere die Summe aller Arbeitsstunden mit dem Stundensatz.",
        "ergebnis": 2857.4,  # (6*7.5 + 4*7.5 + 2*8) * 31.40 = 91 * 31.40
    },
]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "datei_lesen",
            "description": "Liest eine Datei aus dem Projekt und gibt ihren Inhalt zurück.",
            "parameters": {
                "type": "object",
                "properties": {"pfad": {"type": "string", "description": "Pfad, z. B. lager/nord.txt"}},
                "required": ["pfad"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rechnen",
            "description": "Berechnet einen arithmetischen Ausdruck mit + - * / und Klammern. Dezimalpunkt verwenden.",
            "parameters": {
                "type": "object",
                "properties": {"ausdruck": {"type": "string", "description": "z. B. (140 + 86) * 12.5"}},
                "required": ["ausdruck"],
            },
        },
    },
]

SYSTEM = (
    "Du bist ein sorgfältiger Agent. Nutze die Tools, statt zu raten. Rechne nur mit dem Tool rechnen. "
    "Wenn du fertig bist, antworte mit einer Zeile im Format 'ERGEBNIS: <Zahl>'.\n\n"
    "Projektdokumentation (Hintergrund, für die Aufgabe nicht nötig):\n"
)


# ---------------------------------------------------------------------------
# Tools lokal ausführen
# Rechnen über den Syntaxbaum statt eval(): nur Zahlen und Grundrechenarten.
# ---------------------------------------------------------------------------
OPERATOREN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def sicher_rechnen(ausdruck: str) -> float:
    def wert(knoten: ast.AST) -> float:
        if isinstance(knoten, ast.Constant) and isinstance(knoten.value, int | float):
            return float(knoten.value)
        if isinstance(knoten, ast.BinOp) and type(knoten.op) in OPERATOREN:
            return OPERATOREN[type(knoten.op)](wert(knoten.left), wert(knoten.right))
        if isinstance(knoten, ast.UnaryOp) and type(knoten.op) in OPERATOREN:
            return OPERATOREN[type(knoten.op)](wert(knoten.operand))
        raise ValueError("nur Zahlen und + - * / ( ) erlaubt")

    return wert(ast.parse(ausdruck.replace(",", "."), mode="eval").body)


def tool_ausfuehren(name: str, argumente_json: str) -> tuple[str, bool]:
    """Liefert (Ergebnistext, gültig). Ungültige Aufrufe bekommen eine Fehlermeldung zurück."""
    try:
        argumente = json.loads(argumente_json or "{}")
    except json.JSONDecodeError:
        return "Fehler: Argumente sind kein gültiges JSON.", False
    if name == "datei_lesen":
        pfad = str(argumente.get("pfad", "")).strip().lstrip("./")
        return DATEIEN.get(
            pfad, f"Fehler: Datei {pfad!r} nicht gefunden. Vorhanden: {', '.join(DATEIEN)}"
        ), pfad in DATEIEN
    if name == "rechnen":
        try:
            return str(round(sicher_rechnen(str(argumente.get("ausdruck", ""))), 6)), True
        except (ValueError, SyntaxError, ZeroDivisionError) as fehler:
            return f"Fehler: {fehler}", False
    return f"Fehler: unbekanntes Tool {name!r}", False


# ---------------------------------------------------------------------------
# Eine Aufgabe als Agentenschleife
# ---------------------------------------------------------------------------
def loese(ctx, nr: int, doku: str) -> dict:
    aufgabe = AUFGABEN[nr]
    verlauf = [{"role": "system", "content": SYSTEM + doku}, {"role": "user", "content": aufgabe["text"]}]
    aufrufe = gueltig = 0
    zeiten = []
    antwort_text = ""
    for runde in range(1, MAX_RUNDEN + 1):
        antwort = ctx.client.chat(verlauf, max_tokens=8192, tools=TOOLS)
        ctx.merke("agent", antwort, aufgabe=nr, runde=runde)
        zeiten.append(antwort.dauer)
        if not antwort.ok:
            return {
                "aufgabe": nr,
                "erfolg": False,
                "runden": runde,
                "fehler": antwort.fehler[:200],
                "tool_calls": aufrufe,
                "gueltige_tool_calls": gueltig,
                "zeit_pro_runde_s": statistik.kennzahlen(zeiten),
            }
        if not antwort.tool_calls:
            antwort_text = antwort.inhalt
            break
        verlauf.append({"role": "assistant", "content": antwort.inhalt or None, "tool_calls": antwort.tool_calls})
        for i, aufruf in enumerate(antwort.tool_calls):
            aufrufe += 1
            text, ok = tool_ausfuehren(aufruf["function"]["name"], aufruf["function"]["arguments"])
            gueltig += ok
            verlauf.append({"role": "tool", "tool_call_id": aufruf.get("id") or f"call_{runde}_{i}", "content": text})
    wert = ergebnis_lesen(antwort_text)
    erfolg = wert is not None and abs(wert - aufgabe["ergebnis"]) < 0.01
    ctx.log(
        f"Aufgabe {nr}: {'gelöst' if erfolg else 'NICHT gelöst'} in {runde} Runden, {aufrufe} Tool-Calls "
        f"(erwartet {aufgabe['ergebnis']}, bekommen {wert})"
    )
    return {
        "aufgabe": nr,
        "erfolg": erfolg,
        "erwartet": aufgabe["ergebnis"],
        "bekommen": wert,
        "runden": runde,
        "tool_calls": aufrufe,
        "gueltige_tool_calls": gueltig,
        "zeit_pro_runde_s": statistik.kennzahlen(zeiten),
    }


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    doku = texte.fuelltext(DOKU_TOKENS[ctx.stufe], seed=31337, zeichen_pro_token=ctx.zeichen_pro_token)
    aufgaben = [nr for _ in range(WIEDERHOLUNGEN[ctx.stufe]) for nr in range(len(AUFGABEN))]
    ergebnisse = parallel([lambda nr=nr: loese(ctx, nr, doku) for nr in aufgaben], GLEICHZEITIG[ctx.stufe])
    erfolge = sum(e["erfolg"] for e in ergebnisse)
    aufrufe = sum(e["tool_calls"] for e in ergebnisse)
    gueltig = sum(e["gueltige_tool_calls"] for e in ergebnisse)
    return {
        "bestanden": erfolge == len(ergebnisse),
        "kennzahlen": {
            "erfolgsquote": round(erfolge / len(ergebnisse), 3),
            "gueltige_tool_calls_quote": round(gueltig / aufrufe, 3) if aufrufe else None,
            "runden_mittel": round(sum(e["runden"] for e in ergebnisse) / len(ergebnisse), 2),
        },
        "aufgaben": ergebnisse,
    }
