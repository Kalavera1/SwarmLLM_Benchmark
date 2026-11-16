"""Erzeugt reproduzierbare Prompt-Texte in gewünschter Token-Länge.

- Fülltext: technische Dokumentation aus Satzbausteinen. Gleicher Seed = gleicher
  Text, neuer Seed = neuer Text. Ein neuer Seed erzwingt einen kalten Prefill,
  weil der Prefix-Cache nichts wiederverwenden kann.
- Nadel: ein Satz mit einem Code, der irgendwo im Fülltext versteckt wird.
- Kalibrierung: wie viele Zeichen ergeben ein Token beim aktuellen Modell?
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Satzbausteine für den Fülltext
# Bewusst abwechslungsreich, damit der Text nicht zu stark komprimiert und
# Modelle keine Wiederholungsmuster lernen, die die Messung verfälschen.
# ---------------------------------------------------------------------------
KOMPONENTEN = [
    "der Auftragsdienst", "die Lagerverwaltung", "das Rechnungsmodul", "der Export-Job", "die Benutzerverwaltung",
    "der Bestellprozess", "die Schnittstelle zum Spediteur", "das Berichtswesen", "der Preisrechner",
    "die Stammdatenpflege", "der Nachtlauf", "das Mahnwesen", "die Archivierung", "der Druckdienst",
]  # fmt: skip
VERBEN = [
    "liest", "prüft", "berechnet", "sperrt", "aktualisiert", "verwirft", "protokolliert", "überträgt",
    "zerlegt", "bündelt", "sortiert", "verschlüsselt", "bewertet", "freigibt",
]  # fmt: skip
OBJEKTE = [
    "offene Positionen", "Kundenstammsätze", "Belegnummern", "Zeitstempel", "Steuerkennzeichen",
    "Lieferadressen", "Chargen", "Rabattstaffeln", "Kostenstellen", "Fehlermeldungen", "Prüfsummen",
    "Wechselkurse", "Seriennummern", "Buchungskreise",
]  # fmt: skip
BEDINGUNGEN = [
    "sobald der Status auf Freigegeben steht", "wenn die Menge den Schwellwert übersteigt",
    "nur außerhalb der Geschäftszeiten", "nachdem die Sperre aufgehoben wurde", "falls kein Fehler aufgetreten ist",
    "bei jeder Änderung im Mandanten", "vor dem Monatsabschluss", "für alle Werke außer dem Zentrallager",
]  # fmt: skip

STANDARD_ZEICHEN_PRO_TOKEN = 4.0


# ---------------------------------------------------------------------------
# Fülltext in gewünschter Länge
# ---------------------------------------------------------------------------
def fuelltext(ziel_tokens: int, seed: int, zeichen_pro_token: float = STANDARD_ZEICHEN_PRO_TOKEN) -> str:
    """Text mit etwa ziel_tokens Tokens (über zeichen_pro_token geschätzt)."""
    zufall = random.Random(seed)
    ziel_zeichen = int(ziel_tokens * zeichen_pro_token)
    teile: list[str] = []
    laenge = 0
    abschnitt = 1
    while laenge < ziel_zeichen:
        saetze = [f"Abschnitt {seed}.{abschnitt}:"]
        for _ in range(zufall.randint(4, 8)):
            nummer = zufall.randint(100, 99999)
            saetze.append(
                f"{zufall.choice(KOMPONENTEN).capitalize()} {zufall.choice(VERBEN)} {zufall.choice(OBJEKTE)} "
                f"(Vorgang {nummer}) {zufall.choice(BEDINGUNGEN)}."
            )
        absatz = " ".join(saetze) + "\n"
        teile.append(absatz)
        laenge += len(absatz)
        abschnitt += 1
    return "".join(teile)[:ziel_zeichen]


# ---------------------------------------------------------------------------
# Nadel im Heuhaufen
# ---------------------------------------------------------------------------
def nadel_code(seed: int) -> str:
    """Eindeutiger, nicht ratbarer Code, z. B. 'KRANICH-4821'."""
    zufall = random.Random(seed * 7919)
    woerter = ["KRANICH", "LAVENDEL", "OBSIDIAN", "PELIKAN", "ZIMTSTERN", "BASALT", "MISTRAL", "KUMQUAT"]
    return f"{zufall.choice(woerter)}-{zufall.randint(1000, 9999)}"


def nadel_einbauen(text: str, nadel_satz: str, position: float) -> str:
    """Setzt den Satz an die relative Position (0 = Anfang, 1 = Ende), an eine Zeilengrenze."""
    stelle = int(len(text) * min(max(position, 0.0), 1.0))
    zeilenende = text.find("\n", stelle)
    stelle = len(text) if zeilenende == -1 else zeilenende + 1
    return text[:stelle] + nadel_satz + "\n" + text[stelle:]


# ---------------------------------------------------------------------------
# Kalibrierung: Zeichen pro Token
# Bevorzugt exakt über /tokenize (vLLM), sonst über usage.prompt_tokens einer
# kleinen Anfrage, sonst der Standardwert. Ergebnis wird im Kontext gemerkt.
# ---------------------------------------------------------------------------
def kalibrieren(client) -> tuple[float, str]:
    probe = fuelltext(4000, seed=424242)
    anzahl = client.tokens_zaehlen(probe)
    if anzahl:
        return len(probe) / anzahl, "tokenize"
    antwort = client.chat([{"role": "user", "content": probe}], max_tokens=1, stream=False)
    if antwort.ok and antwort.prompt_tokens:
        # Chat-Vorlage kostet ein paar Tokens extra; bei 4000 Tokens vernachlässigbar
        return len(probe) / antwort.prompt_tokens, "usage"
    return STANDARD_ZEICHEN_PRO_TOKEN, "standard"
