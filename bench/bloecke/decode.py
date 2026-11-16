"""Block decode: Wie schnell schreibt das Modell bei 1 bis 64 gleichzeitigen Anfragen?

Pro Stufe starten n Anfragen gleichzeitig. Gemessen:
  pro_nutzer_tok_s   Ausgabetempo, das ein einzelner Nutzer sieht
  gesamt_tok_s       alle erzeugten Tokens / Zeit – Auslastung des Servers
  ttft_s, tpot_ms    Zeit bis zum ersten Token und pro weiterem Token

Die Prompts verlangen natürliche, lange Texte (Bericht über ein Thema). Das
ist wichtig für spekulatives Decoding (MTP, DSpark): Mit Zufallstokens wäre die
Akzeptanzrate unrealistisch niedrig, mit echten Texten realistisch.
"""

from __future__ import annotations

import time

from bench import statistik
from bench.ablauf import parallel

EBENE = "System"
BESCHREIBUNG = "Ausgabetempo pro Nutzer und gesamt bei steigender Parallelität"

STUFEN = {"schnell": [1, 4, 8, 16], "voll": [1, 2, 4, 8, 16, 32, 64]}
AUSGABE_TOKENS = {"schnell": 512, "voll": 1024}
THEMEN = [
    "die Geschichte der Eisenbahn in Deutschland", "die Funktionsweise einer Wärmepumpe",
    "Vor- und Nachteile von Microservices", "den Wasserkreislauf der Erde", "die Planung eines Lagerumzugs",
    "die Entstehung des Rheins", "Grundlagen der doppelten Buchführung", "das Prinzip der Photosynthese",
]  # fmt: skip


# ---------------------------------------------------------------------------
# Eine Stufe mit n gleichzeitigen Anfragen
# ---------------------------------------------------------------------------
def stufe(ctx, n: int, ausgabe: int) -> dict:
    def anfrage(i: int):
        thema = THEMEN[i % len(THEMEN)]
        prompt = f"Schreibe einen ausführlichen, gut gegliederten Bericht über {thema}. Mindestens 1500 Wörter."
        antwort = ctx.client.chat([{"role": "user", "content": prompt}], max_tokens=ausgabe, extra=ctx.denk_extra())
        ctx.merke("decode", antwort, parallel=n)
        return antwort

    start = time.monotonic()
    antworten = parallel([lambda i=i: anfrage(i) for i in range(n)], n)
    wand = time.monotonic() - start
    ok = [a for a in antworten if a.ok]
    tokens = sum(a.ausgabe_tokens for a in ok)
    ergebnis = {
        "parallel": n,
        "erfolgreich": len(ok),
        "gesamt_tok_s": round(tokens / wand, 1) if wand else None,
        "pro_nutzer_tok_s": statistik.kennzahlen(a.decode_tok_s for a in ok),
        "ttft_s": statistik.kennzahlen(a.ttft for a in ok),
        "tpot_ms": statistik.kennzahlen((a.tpot * 1000 if a.tpot else None) for a in ok),
        "ausgabe_tokens_mittel": round(tokens / len(ok)) if ok else 0,
        "fehler": [a.fehler[:120] for a in antworten if not a.ok][:3],
    }
    ctx.log(
        f"{n:>3} parallel: pro Nutzer p50 {ergebnis['pro_nutzer_tok_s'].get('p50')} tok/s, "
        f"gesamt {ergebnis['gesamt_tok_s']} tok/s, TTFT p90 {ergebnis['ttft_s'].get('p90')} s"
    )
    return ergebnis


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    ausgabe = AUSGABE_TOKENS[ctx.stufe]
    ergebnisse = [stufe(ctx, n, ausgabe) for n in STUFEN[ctx.stufe]]
    return {
        "bestanden": None,  # reine Messung, bewertet wird im Lastmix gegen Zielwerte
        "kennzahlen": {
            f"pro_nutzer_tok_s_p50_bei_{e['parallel']}": e["pro_nutzer_tok_s"].get("p50") for e in ergebnisse
        }
        | {f"gesamt_tok_s_bei_{e['parallel']}": e["gesamt_tok_s"] for e in ergebnisse},
        "stufen": ergebnisse,
    }
