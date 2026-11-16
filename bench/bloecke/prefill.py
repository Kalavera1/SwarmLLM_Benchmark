"""Block prefill: Wie lange dauert das Einlesen langer Prompts?

Für jede Länge zwei Messungen:
  kalt   neuer Text, nichts im Prefix-Cache -> echtes Einlesen
  warm   derselbe Text noch einmal -> zeigt, was der Prefix-Cache spart
Gemessen wird die Zeit bis zum ersten Token und daraus das Einlesetempo.

500k ist Pflicht schon in der Schnellstufe (Projektziel). Passt eine Länge nicht
in den Kontext des Modells, wird sie übersprungen und als „nicht erreichbar“
vermerkt – für 500k zählt das als nicht bestanden.
"""

from __future__ import annotations

from bench import texte

EBENE = "System"
BESCHREIBUNG = "Zeit bis zum ersten Token bei 8k bis 1M Tokens, kalt und warm"

LAENGEN = {
    "schnell": [8_000, 128_000, 500_000],
    "voll": [8_000, 32_000, 128_000, 256_000, 500_000, 1_000_000],
}
PFLICHT = 500_000
RESERVE = 2_048  # Platz für Frage, Chat-Vorlage und Antwort


# ---------------------------------------------------------------------------
# Eine Messung
# ---------------------------------------------------------------------------
def messe(ctx, text: str, laenge: int, art: str) -> dict:
    nachrichten = [{"role": "user", "content": text + "\n\nFasse den Text in einem Satz zusammen."}]
    antwort = ctx.client.chat(nachrichten, max_tokens=16, extra=ctx.denk_extra())
    ctx.merke("prefill", antwort, ziel_tokens=laenge, messung=art)
    tokens = antwort.prompt_tokens or int(len(text) / ctx.zeichen_pro_token)
    tempo = tokens / antwort.ttft if antwort.ok and antwort.ttft else None
    ctx.log(
        f"{laenge // 1000:>5}k {art:<4} erstes Token: "
        f"{(f'{antwort.ttft:7.2f} s' if antwort.ttft else '   -   ')}  "
        f"Einlesen: {(f'{tempo:8.0f} tok/s' if tempo else '-')}  {antwort.fehler[:80]}"
    )
    return {
        "ok": antwort.ok,
        "prompt_tokens": tokens,
        "ttft_s": round(antwort.ttft, 3) if antwort.ttft else None,
        "prefill_tok_s": round(tempo) if tempo else None,
        "fehler": antwort.fehler[:200] or None,
    }


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    grenze = ctx.max_kontext() - RESERVE
    messungen = []
    for nr, laenge in enumerate(LAENGEN[ctx.stufe]):
        if laenge > grenze:
            ctx.log(f"{laenge // 1000:>5}k übersprungen: Kontext des Modells nur {grenze + RESERVE}")
            messungen.append({"ziel_tokens": laenge, "uebersprungen": "Kontext zu klein"})
            continue
        text = texte.fuelltext(laenge, seed=1000 + nr, zeichen_pro_token=ctx.zeichen_pro_token)
        kalt = messe(ctx, text, laenge, "kalt")
        warm = messe(ctx, text, laenge, "warm")
        messungen.append({"ziel_tokens": laenge, "kalt": kalt, "warm": warm})

    pflicht = next((m for m in messungen if m["ziel_tokens"] == PFLICHT), None)
    pflicht_ok = bool(pflicht and pflicht.get("kalt", {}).get("ok"))
    alle_ok = all(m.get("kalt", {}).get("ok") and m.get("warm", {}).get("ok") for m in messungen if "kalt" in m)
    return {
        "bestanden": pflicht_ok and alle_ok,
        "kennzahlen": {f"ttft_kalt_{m['ziel_tokens'] // 1000}k_s": m.get("kalt", {}).get("ttft_s") for m in messungen}
        | {f"ttft_warm_{m['ziel_tokens'] // 1000}k_s": m.get("warm", {}).get("ttft_s") for m in messungen}
        | {"500k_erreichbar": pflicht_ok},
        "messungen": messungen,
    }
