"""Block nadel: Findet das Modell eine Information tief im langen Kontext?

Ein Satz mit einem eindeutigen Code („Der geheime Projektcode lautet KRANICH-4821.“)
wird an einer bestimmten Stelle im Fülltext versteckt. Das Modell soll den Code
nennen. 500k ist Pflicht schon in der Schnellstufe.
"""

from __future__ import annotations

from bench import texte, waechter

EBENE = "System"
BESCHREIBUNG = "Code im langen Kontext wiederfinden (Nadeltest), 500k Pflicht"

LAENGEN = {"schnell": [128_000, 500_000], "voll": [32_000, 128_000, 256_000, 500_000, 1_000_000]}
POSITIONEN = {"schnell": [0.5], "voll": [0.1, 0.5, 0.9]}
PFLICHT = 500_000
RESERVE = 4_096


# ---------------------------------------------------------------------------
# Ein Durchgang
# ---------------------------------------------------------------------------
def durchgang(ctx, laenge: int, position: float, seed: int) -> dict:
    code = texte.nadel_code(seed)
    text = texte.fuelltext(laenge, seed=seed, zeichen_pro_token=ctx.zeichen_pro_token)
    text = texte.nadel_einbauen(text, f"Wichtig: Der geheime Projektcode lautet {code}.", position)
    frage = "Wie lautet der geheime Projektcode, der im Text genannt wird? Antworte nur mit dem Code."
    antwort = ctx.client.chat([{"role": "user", "content": text + "\n\n" + frage}], max_tokens=8192)
    ctx.merke("nadel", antwort, ziel_tokens=laenge, position=position)
    gefunden = antwort.ok and code.lower() in antwort.inhalt.lower()
    ctx.log(
        f"{laenge // 1000:>5}k Position {position:.0%}: {'gefunden' if gefunden else 'NICHT gefunden'} "
        f"(erwartet {code}, Antwort {antwort.inhalt.strip()[:40]!r}, {antwort.dauer:.0f} s)"
    )
    return {
        "ziel_tokens": laenge,
        "position": position,
        "gefunden": gefunden,
        "prompt_tokens": antwort.prompt_tokens,
        "ttft_s": round(antwort.ttft, 2) if antwort.ttft else None,
        "kaputt": waechter.ist_kaputt(antwort.inhalt, antwort.denken),
        "fehler": antwort.fehler[:200] or None,
    }


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    grenze = ctx.max_kontext() - RESERVE
    ergebnisse = []
    seed = 5000
    for laenge in LAENGEN[ctx.stufe]:
        if laenge > grenze:
            ctx.log(f"{laenge // 1000:>5}k übersprungen: Kontext des Modells zu klein")
            ergebnisse.append({"ziel_tokens": laenge, "uebersprungen": "Kontext zu klein"})
            continue
        for position in POSITIONEN[ctx.stufe]:
            seed += 1
            ergebnisse.append(durchgang(ctx, laenge, position, seed))

    gemessen = [e for e in ergebnisse if "gefunden" in e]
    treffer = sum(e["gefunden"] for e in gemessen)
    pflicht = [e for e in gemessen if e["ziel_tokens"] == PFLICHT]
    return {
        "bestanden": bool(pflicht) and all(e["gefunden"] for e in pflicht) and treffer == len(gemessen),
        "kennzahlen": {
            "gefunden": treffer,
            "gesamt": len(gemessen),
            "500k_gefunden": all(e["gefunden"] for e in pflicht) if pflicht else False,
        },
        "durchgaenge": ergebnisse,
    }
