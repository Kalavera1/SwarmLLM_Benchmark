"""Block waechter: Liefert das Modell überhaupt brauchbare Antworten?

Fünf kurze Fragen mit bekannter Antwort, erst einzeln, dann alle gleichzeitig
(manche Kernel-Fehler zeigen sich erst, wenn Anfragen gebündelt laufen). Jede
Antwort geht zusätzlich durch die Schleifen- und Wiederholungserkennung.

Läuft als Erstes: Besteht ein Modell den Wächter nicht, sind alle späteren
Durchsatzwerte wertlos – und der Pod kann sofort gelöscht werden.
"""

from __future__ import annotations

from bench import waechter
from bench.ablauf import parallel

EBENE = "System"
BESCHREIBUNG = "Bekannte Antworten und Erkennung kaputter Ausgaben, einzeln und gebündelt"

# ---------------------------------------------------------------------------
# Fragen: (Prompt, erwartete Teile der Antwort, alle müssen vorkommen)
# ---------------------------------------------------------------------------
FRAGEN = [
    ("Was ist die Hauptstadt von Frankreich? Antworte mit einem Wort.", ["paris"]),
    ("Rechne 17 * 23. Antworte nur mit der Zahl.", ["391"]),
    ("Welche drei Farben hat die Flagge Deutschlands? Nenne sie von oben nach unten.", ["schwarz", "rot", "gold"]),
    ("Schreibe drei vollständige Sätze über den Rhein.", ["rhein"]),
    ("Schreibe eine Python-Funktion ist_primzahl(n), die prüft, ob n eine Primzahl ist.", ["def ist_primzahl"]),
]


# ---------------------------------------------------------------------------
# Eine Frage stellen und bewerten
# ---------------------------------------------------------------------------
def frage(ctx, nr: int, durchgang: str) -> dict:
    prompt, erwartet = FRAGEN[nr]
    antwort = ctx.client.chat([{"role": "user", "content": prompt}], max_tokens=8192, extra=ctx.denk_extra())
    ctx.merke("waechter", antwort, frage=nr, durchgang=durchgang)
    text = antwort.inhalt.lower()
    analyse = waechter.analyse(antwort.inhalt, antwort.denken)
    richtig = antwort.ok and all(teil in text for teil in erwartet)
    return {
        "frage": nr,
        "durchgang": durchgang,
        "richtig": richtig,
        "kaputt": analyse["kaputt"],
        "gruende": analyse["gruende"] + ([] if antwort.ok else [f"HTTP {antwort.status}: {antwort.fehler[:100]}"]),
        "antwort_anfang": antwort.inhalt[:200],
        "tok_s": antwort.decode_tok_s,
    }


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    einzeln = [frage(ctx, i, "einzeln") for i in range(len(FRAGEN))]
    gebuendelt = parallel([lambda i=i: frage(ctx, i, "gebündelt") for i in range(len(FRAGEN))], len(FRAGEN))
    alle = einzeln + gebuendelt
    for e in alle:
        zeichen = "ok    " if e["richtig"] and not e["kaputt"] else "FEHLER"
        ctx.log(f"{zeichen} Frage {e['frage']} ({e['durchgang']}): {e['antwort_anfang'][:60]!r} {e['gruende']}")

    richtig = sum(e["richtig"] for e in alle)
    kaputt = sum(e["kaputt"] for e in alle)
    return {
        "bestanden": kaputt == 0 and richtig == len(alle),
        "kennzahlen": {"richtig": richtig, "gesamt": len(alle), "kaputt": kaputt},
        "antworten": alle,
    }
