"""Block rechnen: Rechenaufgaben mit bekannter Lösung bei verschiedenen Denktiefen.

Zeigt, was Denken kostet und bringt: Für jede Denkstufe aus dem Profil (z. B.
aus / an) werden dieselben Aufgaben gestellt. Gemessen: richtig/falsch,
Denk-Tokens und Dauer. Erfahrung B300: Standard-Denktiefe erzeugte bei Code
11–23k Denk-Tokens; deshalb max_tokens 32k.
"""

from __future__ import annotations

from bench.zahlen import ergebnis_lesen

EBENE = "Abnahme"
BESCHREIBUNG = "Rechenaufgaben mit bekannter Lösung je Denkstufe, mit Denk-Tokens und Dauer"

AUFGABEN = [
    ("Berechne (347 * 29) - (1584 / 12) + 2^10.", 10955.0),
    (
        "Ein Händler kauft 240 Artikel zu je 3,75 €. Er verkauft 85 % davon zu je 6,20 € und den Rest zu je 2,10 €. "
        "Wie hoch ist sein Gewinn in Euro?",
        440.4,
    ),
    ("Wie viele ganze Zahlen von 1 bis 1000 sind durch 3 oder 5 teilbar, aber nicht durch 7?", 401.0),
]
ANHANG = "\n\nGib am Ende eine Zeile im Format 'ERGEBNIS: <Zahl>' aus."


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    ergebnisse = []
    for stufe, extra in ctx.profil.denkstufen.items():
        for nr, (frage, loesung) in enumerate(AUFGABEN):
            antwort = ctx.client.chat([{"role": "user", "content": frage + ANHANG}], max_tokens=32768, extra=extra)
            ctx.merke("rechnen", antwort, denkstufe=stufe, aufgabe=nr)
            wert = ergebnis_lesen(antwort.inhalt)
            richtig = wert is not None and abs(wert - loesung) < 0.01
            denk_tokens = antwort.reasoning_tokens
            if denk_tokens is None and antwort.denken:
                denk_tokens = int(len(antwort.denken) / ctx.zeichen_pro_token)  # geschätzt
            ctx.log(
                f"{stufe:<8} Aufgabe {nr}: {'richtig' if richtig else 'FALSCH'} ({wert}), "
                f"Denken ≈ {denk_tokens} Tokens, {antwort.dauer:.0f} s"
            )
            ergebnisse.append(
                {
                    "denkstufe": stufe,
                    "aufgabe": nr,
                    "richtig": richtig,
                    "erwartet": loesung,
                    "bekommen": wert,
                    "denk_tokens": denk_tokens,
                    "ausgabe_tokens": antwort.completion_tokens,
                    "dauer_s": round(antwort.dauer, 1),
                    "fehler": antwort.fehler[:200] or None,
                }
            )

    je_stufe = {}
    for stufe in ctx.profil.denkstufen:
        teil = [e for e in ergebnisse if e["denkstufe"] == stufe]
        je_stufe[stufe] = {
            "richtig": sum(e["richtig"] for e in teil),
            "gesamt": len(teil),
            "dauer_s_summe": round(sum(e["dauer_s"] for e in teil), 1),
        }
    return {
        "bestanden": any(s["richtig"] == s["gesamt"] for s in je_stufe.values()),
        "kennzahlen": je_stufe,
        "aufgaben": ergebnisse,
    }
