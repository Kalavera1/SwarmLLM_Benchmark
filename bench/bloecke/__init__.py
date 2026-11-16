"""Verzeichnis aller Testblöcke in empfohlener Reihenfolge.

Jeder Block ist ein Modul mit:
  EBENE          Unit, Integration, System oder Abnahme (V-Modell)
  BESCHREIBUNG   eine Zeile für `python3 -m bench liste`
  ausfuehren()   bekommt den Kontext, liefert ein Wörterbuch mit mindestens
                 "bestanden" (True, False oder None = reine Messung)
Optional: AUFWAERMEN = False, wenn der Block keine Aufwärmrunde braucht.

Reihenfolge = Laufreihenfolge bei `alle`: Erst die billigen Prüfungen, die einen
kaputten Server früh entlarven (Integration, Wächter). Schlägt eine davon fehl,
bricht `alle` ab, bevor die teuren Blöcke GPU-Zeit verbrauchen.
"""

from __future__ import annotations

from bench.bloecke import abap, agent, bilder, decode, integration, lastmix, nadel, prefill, rechnen, waechter

BLOECKE = {
    "integration": integration,
    "waechter": waechter,
    "prefill": prefill,
    "decode": decode,
    "nadel": nadel,
    "agent": agent,
    "bilder": bilder,
    "lastmix": lastmix,
    "rechnen": rechnen,
    "abap": abap,
}

# Blöcke, deren Fehlschlag einen Lauf mit `alle` sofort beendet (spart GPU-Zeit)
TORWAECHTER = ("integration", "waechter")
