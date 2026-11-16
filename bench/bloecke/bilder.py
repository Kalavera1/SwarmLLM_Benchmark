"""Block bilder: Versteht das Modell Bilder, und was kosten sie an Zeit?

Zwei Teile:
  Eval     Bilder mit farbigen Quadraten, Frage nach der Anzahl einer Farbe.
           Die richtige Antwort steht fest (Bilder werden hier erzeugt).
  Tempo    Zeit bis zum ersten Token mit 0, 1 und 4 Bildern, einzeln und mit
           4 gleichzeitigen Anfragen – Bilder machen den Prefill teurer.
Profile ohne Bildfähigkeit (VISION=0) überspringen den Block.
"""

from __future__ import annotations

import random
import re

from bench import bilder, statistik
from bench.ablauf import parallel

EBENE = "Abnahme"
BESCHREIBUNG = "Quadrate zählen (bekannte Antwort) und Zeit bis zum ersten Token mit 0/1/4 Bildern"

EVAL_ANZAHL = {"schnell": 6, "voll": 12}
TEMPO_BILDER = [0, 1, 4]
TEMPO_PARALLEL = [1, 4]
ZAHLWOERTER = {"null": 0, "eins": 1, "ein": 1, "eine": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6}


# ---------------------------------------------------------------------------
# Antwort in eine Zahl übersetzen (Ziffer oder Zahlwort)
# ---------------------------------------------------------------------------
def zahl_aus_antwort(text: str) -> int | None:
    treffer = re.search(r"\d+", text)
    if treffer:
        return int(treffer.group())
    for wort in re.findall(r"[a-zäöü]+", text.lower()):
        if wort in ZAHLWOERTER:
            return ZAHLWOERTER[wort]
    return None


# ---------------------------------------------------------------------------
# Eval: Quadrate einer Farbe zählen
# ---------------------------------------------------------------------------
def eval_aufgabe(ctx, nr: int) -> dict:
    zufall = random.Random(nr)
    farben = zufall.sample(list(bilder.FARBEN), 2)
    anzahl = {farben[0]: zufall.randint(1, 6), farben[1]: zufall.randint(1, 5)}
    png = bilder.quadrate_bild(anzahl, seed=nr)
    frage = f"Wie viele {farben[0]}e Quadrate sind auf dem Bild? Antworte nur mit der Zahl."
    inhalt = [bilder.bild_inhalt(png), {"type": "text", "text": frage}]
    antwort = ctx.client.chat([{"role": "user", "content": inhalt}], max_tokens=4096, extra=ctx.denk_extra())
    ctx.merke("bilder-eval", antwort, aufgabe=nr)
    bekommen = zahl_aus_antwort(antwort.inhalt) if antwort.ok else None
    richtig = bekommen == anzahl[farben[0]]
    ctx.log(f"Bild {nr}: {farben[0]} erwartet {anzahl[farben[0]]}, bekommen {bekommen} {'ok' if richtig else 'FALSCH'}")
    return {
        "aufgabe": nr,
        "farbe": farben[0],
        "erwartet": anzahl[farben[0]],
        "bekommen": bekommen,
        "richtig": richtig,
        "fehler": antwort.fehler[:200] or None,
    }


# ---------------------------------------------------------------------------
# Tempo: Zeit bis zum ersten Token mit k Bildern bei n gleichzeitigen Anfragen
# ---------------------------------------------------------------------------
def tempo(ctx, k: int, n: int) -> dict:
    def anfrage(i: int):
        teile = [
            bilder.bild_inhalt(bilder.quadrate_bild({"blau": 2, "rot": 1}, seed=100 * k + i + j)) for j in range(k)
        ]
        teile.append({"type": "text", "text": f"Beschreibe kurz, was du siehst. (Anfrage {i})"})
        antwort = ctx.client.chat([{"role": "user", "content": teile}], max_tokens=64, extra=ctx.denk_extra())
        ctx.merke("bilder-tempo", antwort, bilder=k, parallel=n)
        return antwort

    antworten = parallel([lambda i=i: anfrage(i) for i in range(n)], n)
    ok = [a for a in antworten if a.ok]
    ergebnis = {"bilder": k, "parallel": n, "erfolgreich": len(ok), "ttft_s": statistik.kennzahlen(a.ttft for a in ok)}
    ctx.log(f"{k} Bilder, {n} parallel: TTFT p50 {ergebnis['ttft_s'].get('p50')} s")
    return ergebnis


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    if not ctx.profil.kann_bilder:
        return {"bestanden": None, "uebersprungen": "Profil ohne Bildfähigkeit (VISION=0)"}
    evals = [eval_aufgabe(ctx, nr) for nr in range(EVAL_ANZAHL[ctx.stufe])]
    tempi = [tempo(ctx, k, n) for k in TEMPO_BILDER for n in TEMPO_PARALLEL]
    richtig = sum(e["richtig"] for e in evals)
    return {
        "bestanden": richtig / len(evals) >= 0.8,
        "kennzahlen": {"richtig": richtig, "gesamt": len(evals)}
        | {f"ttft_p50_{t['bilder']}_bilder_{t['parallel']}_parallel_s": t["ttft_s"].get("p50") for t in tempi},
        "eval": evals,
        "tempo": tempi,
    }
