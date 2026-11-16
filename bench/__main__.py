"""Kommandozeile der Testsuite.

Beispiele:
  python3 -m bench liste
  python3 -m bench run integration waechter --profil mock
  python3 -m bench run alle --profil qwen38-27b --stufe schnell
  python3 -m bench auswertung
"""

from __future__ import annotations

import argparse
import sys

from bench import auswertung
from bench.ablauf import Kontext, fuehre_block_aus
from bench.bloecke import BLOECKE, TORWAECHTER
from bench.client import Client
from bench.konfig import ERGEBNIS_ORDNER, lade_profil, ziel_aufloesen


# ---------------------------------------------------------------------------
# Befehl "liste": alle Blöcke mit Ebene und Beschreibung
# ---------------------------------------------------------------------------
def befehl_liste(_args) -> int:
    for name, modul in BLOECKE.items():
        print(f"{name:<12} {modul.EBENE:<12} {modul.BESCHREIBUNG}")
    return 0


# ---------------------------------------------------------------------------
# Befehl "run": Blöcke gegen ein Ziel ausführen
# ---------------------------------------------------------------------------
def befehl_run(args) -> int:
    namen = list(BLOECKE) if args.bloecke == ["alle"] else args.bloecke
    unbekannt = [n for n in namen if n not in BLOECKE]
    if unbekannt:
        print(f"Unbekannte Blöcke: {', '.join(unbekannt)}. Verfügbar: {', '.join(BLOECKE)}, alle", file=sys.stderr)
        return 2

    profil = lade_profil(args.profil)
    ziel = ziel_aufloesen(profil, args.ziel, args.ueber_gateway)
    if profil.key_pflicht and not ziel.api_key:
        print(
            "FEHLER: kein API-Key gefunden (VLLM_API_KEY in benchmark.conf oder Pod-Datei). Regel 8.", file=sys.stderr
        )
        return 2

    ctx = Kontext(profil=profil, ziel=ziel, client=Client(ziel.basis_url, ziel.api_key, ziel.modell), stufe=args.stufe)
    kosten = f", {ziel.kosten_pro_stunde:.2f} $/h" if ziel.kosten_pro_stunde else ""
    print(f"Profil {profil.name}, Modell {ziel.modell}, Ziel {ziel.basis_url}, Stufe {args.stufe}{kosten}")

    fehlgeschlagen = []
    for name in namen:
        ergebnis = fuehre_block_aus(ctx, name, BLOECKE[name])
        if ergebnis.get("bestanden") is False:
            fehlgeschlagen.append(name)
            if args.bloecke == ["alle"] and name in TORWAECHTER and not args.weiter:
                print(f"\nAbbruch: {name} nicht bestanden – teure Blöcke werden nicht gestartet (--weiter erzwingt).")
                break

    print(f"\nFertig. Nicht bestanden: {', '.join(fehlgeschlagen) or 'keiner'}")
    return 1 if fehlgeschlagen else 0


# ---------------------------------------------------------------------------
# Befehl "auswertung": Vergleichstabelle aus den letzten Ergebnissen
# ---------------------------------------------------------------------------
def befehl_auswertung(args) -> int:
    text = auswertung.tabelle(ERGEBNIS_ORDNER, args.profil)
    print(text)
    if args.speichern:
        ziel = ERGEBNIS_ORDNER / "zusammenfassung.md"
        ziel.write_text(text + "\n", encoding="utf-8")
        print(f"\nGespeichert: {ziel}")
    return 0


# ---------------------------------------------------------------------------
# Argumente
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m bench", description="Testsuite für SwarmLLM_Benchmark")
    befehle = ap.add_subparsers(dest="befehl", required=True)

    befehle.add_parser("liste", help="alle Blöcke anzeigen").set_defaults(func=befehl_liste)

    run = befehle.add_parser("run", help="Blöcke ausführen")
    run.add_argument("bloecke", nargs="+", help="Blocknamen oder 'alle'")
    run.add_argument("--profil", required=True, help="Ordnername unter profiles/")
    run.add_argument("--stufe", choices=["schnell", "voll"], default="schnell")
    run.add_argument("--ziel", help="Basis-URL mit /v1, überschreibt Profil und Pod-Datei")
    run.add_argument("--ueber-gateway", action="store_true", help="über LiteLLM statt direkt an vLLM")
    run.add_argument("--weiter", action="store_true", help="bei 'alle' auch nach fehlgeschlagenem Wächter weitermachen")
    run.set_defaults(func=befehl_run)

    aus = befehle.add_parser("auswertung", help="Vergleichstabelle der letzten Ergebnisse")
    aus.add_argument("--profil", help="nur dieses Profil")
    aus.add_argument("--speichern", action="store_true", help="als results/zusammenfassung.md speichern")
    aus.set_defaults(func=befehl_auswertung)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
