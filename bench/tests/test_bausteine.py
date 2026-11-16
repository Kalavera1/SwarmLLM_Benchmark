"""Unit-Tests für die Bausteine der Testsuite (Ebene Unit im V-Modell).

Prüft die eigenen Rechen- und Hilfsfunktionen ohne Server: Statistik,
Wächter, Zahlen lesen, Texte, Bilder, Konfiguration, Prometheus-Parser,
Tools der Agentenschleife und die ABAP-Kriterien.

Aufruf: python3 -m unittest discover -s bench/tests -t . -v
"""

from __future__ import annotations

import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from bench import bilder, statistik, texte, waechter, zahlen
from bench.ablauf import zaehler_differenz
from bench.bloecke import abap, agent
from bench.bloecke.bilder import zahl_aus_antwort
from bench.client import parse_prometheus
from bench.konfig import Profil, lies_env_datei


# ---------------------------------------------------------------------------
# Statistik
# ---------------------------------------------------------------------------
class TestStatistik(unittest.TestCase):
    def test_perzentil_interpoliert_linear(self):
        self.assertEqual(statistik.perzentil([1, 2, 3, 4], 50), 2.5)
        self.assertEqual(statistik.perzentil([10], 90), 10)
        self.assertIsNone(statistik.perzentil([], 50))

    def test_none_werte_werden_ignoriert(self):
        k = statistik.kennzahlen([None, 1.0, 3.0, None])
        self.assertEqual(k["anzahl"], 2)
        self.assertEqual(k["mittel"], 2.0)

    def test_leere_reihe(self):
        self.assertEqual(statistik.kennzahlen([]), {"anzahl": 0})


# ---------------------------------------------------------------------------
# Wächter: kaputte Ausgaben erkennen, normale durchlassen
# ---------------------------------------------------------------------------
class TestWaechter(unittest.TestCase):
    def test_normaler_text_ist_nicht_kaputt(self):
        text = texte.fuelltext(500, seed=1)
        self.assertFalse(waechter.ist_kaputt(text))

    def test_endlosschleife_wird_erkannt(self):
        self.assertTrue(waechter.ist_kaputt("Antwort: " + "lock" * 50))

    def test_leere_antwort_ist_kaputt(self):
        self.assertTrue(waechter.ist_kaputt("", ""))

    def test_trennlinien_und_tabellen_sind_kein_fehler(self):
        text = "Ergebnis\n" + "=" * 60 + "\n| a | b |\n|---|---|\n| 1 | 2 |\n"
        self.assertFalse(waechter.ist_kaputt(text))

    def test_wiederholte_saetze_werden_erkannt(self):
        satz = "Die Antwort ist leider nicht eindeutig bestimmbar, wie bereits gesagt wurde. "
        self.assertTrue(waechter.analyse(satz * 20)["kaputt"])


# ---------------------------------------------------------------------------
# Zahlen aus Antworten lesen
# ---------------------------------------------------------------------------
class TestZahlen(unittest.TestCase):
    def test_schreibweisen(self):
        faelle = {
            "ERGEBNIS: 2825": 2825.0,
            "ERGEBNIS: 2.825,00": 2825.0,
            "ERGEBNIS: 2,825.00": 2825.0,
            "ERGEBNIS: 440,40": 440.4,
            "ERGEBNIS: 10.955": 10955.0,
            "ERGEBNIS: **848**": 848.0,
            "Zwischenschritt ERGEBNIS: 1\nERGEBNIS: 401.": 401.0,
        }
        for text, erwartet in faelle.items():
            with self.subTest(text=text):
                self.assertEqual(zahlen.ergebnis_lesen(text), erwartet)

    def test_ohne_ergebnis(self):
        self.assertIsNone(zahlen.ergebnis_lesen("keine Zahl"))

    def test_zahlwort_im_bildblock(self):
        self.assertEqual(zahl_aus_antwort("Ich sehe drei rote Quadrate."), 3)
        self.assertEqual(zahl_aus_antwort("4"), 4)


# ---------------------------------------------------------------------------
# Texte: Länge, Reproduzierbarkeit, Nadel
# ---------------------------------------------------------------------------
class TestTexte(unittest.TestCase):
    def test_laenge_und_reproduzierbarkeit(self):
        a = texte.fuelltext(1000, seed=7, zeichen_pro_token=4.0)
        self.assertEqual(len(a), 4000)
        self.assertEqual(a, texte.fuelltext(1000, seed=7, zeichen_pro_token=4.0))
        self.assertNotEqual(a, texte.fuelltext(1000, seed=8, zeichen_pro_token=4.0))

    def test_nadel_steht_an_der_richtigen_stelle(self):
        text = texte.fuelltext(2000, seed=3)
        mit = texte.nadel_einbauen(text, "NADEL", 0.5)
        stelle = mit.index("NADEL") / len(mit)
        self.assertTrue(0.4 < stelle < 0.6)
        self.assertEqual(texte.nadel_code(5), texte.nadel_code(5))


# ---------------------------------------------------------------------------
# Bilder: gültiges PNG mit richtiger Größe
# ---------------------------------------------------------------------------
class TestBilder(unittest.TestCase):
    def test_png_ist_gueltig(self):
        roh = bilder.quadrate_bild({"rot": 3, "blau": 2}, seed=1, groesse=128)
        self.assertTrue(roh.startswith(b"\x89PNG\r\n\x1a\n"))
        breite, hoehe = struct.unpack(">II", roh[16:24])
        self.assertEqual((breite, hoehe), (128, 128))
        # IDAT entpacken: 128 Zeilen à (1 Filterbyte + 128*3)
        start = roh.index(b"IDAT") + 4
        laenge = struct.unpack(">I", roh[start - 8 : start - 4])[0]
        self.assertEqual(len(zlib.decompress(roh[start : start + laenge])), 128 * (1 + 128 * 3))

    def test_rote_pixel_vorhanden(self):
        roh = bilder.quadrate_bild({"rot": 1}, seed=2, groesse=128)
        self.assertIn(b"data:image/png;base64,", bilder.data_url(roh).encode())

    def test_zu_viele_quadrate(self):
        with self.assertRaises(ValueError):
            bilder.quadrate_bild({"rot": 17}, seed=1, groesse=128)


# ---------------------------------------------------------------------------
# Konfiguration: .env lesen, Denkstufen
# ---------------------------------------------------------------------------
class TestKonfig(unittest.TestCase):
    def test_env_datei(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "profile.env"
            pfad.write_text(
                "# Kommentar\nexport A=1\nB='x y'\nDENKSTUFEN='aus={\"t\":false};an={}'\n", encoding="utf-8"
            )
            werte = lies_env_datei(pfad)
        self.assertEqual(werte["A"], "1")
        self.assertEqual(werte["B"], "x y")
        profil = Profil("test", werte)
        self.assertEqual(profil.denkstufen, {"aus": {"t": False}, "an": {}})

    def test_standardwerte(self):
        profil = Profil("p", {})
        self.assertTrue(profil.key_pflicht)
        self.assertFalse(profil.kann_bilder)
        self.assertEqual(profil.denkstufen, {"standard": {}})


# ---------------------------------------------------------------------------
# vLLM-Zähler
# ---------------------------------------------------------------------------
class TestMetriken(unittest.TestCase):
    TEXT = (
        "# HELP x\n"
        'vllm:prefix_cache_queries_total{model_name="m"} 100.0\n'
        'vllm:prefix_cache_hits_total{model_name="m"} 40.0\n'
        'vllm:spec_decode_num_draft_tokens_total{model_name="m",x="1"} 30.0\n'
        'vllm:spec_decode_num_draft_tokens_total{model_name="m",x="2"} 30.0\n'
        'vllm:spec_decode_num_accepted_tokens_total{model_name="m"} 45.0\n'
        "process_cpu_seconds_total 5\n"
    )

    def test_parser_summiert_labels(self):
        werte = parse_prometheus(self.TEXT)
        self.assertEqual(werte["vllm:spec_decode_num_draft_tokens_total"], 60.0)
        self.assertNotIn("process_cpu_seconds_total", werte)

    def test_abgeleitete_quoten(self):
        nachher = parse_prometheus(self.TEXT)
        vorher = {k: 0.0 for k in nachher}
        diff = zaehler_differenz(vorher, nachher)
        self.assertEqual(diff["abgeleitet"]["prefix_cache_trefferquote"], 0.4)
        self.assertEqual(diff["abgeleitet"]["spec_decode_akzeptanz"], 0.75)
        self.assertEqual(zaehler_differenz({}, nachher), {})


# ---------------------------------------------------------------------------
# Agentenschleife: Tools
# ---------------------------------------------------------------------------
class TestAgentTools(unittest.TestCase):
    def test_sicher_rechnen(self):
        self.assertEqual(agent.sicher_rechnen("(140 + 86) * 12,5"), 2825.0)
        with self.assertRaises(ValueError):
            agent.sicher_rechnen("__import__('os').system('x')")

    def test_tool_ausfuehren(self):
        text, ok = agent.tool_ausfuehren("datei_lesen", '{"pfad": "./lager/nord.txt"}')
        self.assertTrue(ok)
        self.assertIn("A-17: 140", text)
        self.assertEqual(agent.tool_ausfuehren("rechnen", '{"ausdruck": "91 * 31.4"}'), ("2857.4", True))
        self.assertFalse(agent.tool_ausfuehren("datei_lesen", "kein json")[1])
        self.assertFalse(agent.tool_ausfuehren("loeschen", "{}")[1])

    def test_aufgaben_loesungen_stimmen(self):
        self.assertEqual(agent.AUFGABEN[0]["ergebnis"], (140 + 86) * 12.50)
        self.assertEqual(agent.AUFGABEN[1]["ergebnis"], round((55 + 210) * 3.20, 2))
        self.assertAlmostEqual(agent.AUFGABEN[2]["ergebnis"], (6 * 7.5 + 4 * 7.5 + 2 * 8) * 31.40)


# ---------------------------------------------------------------------------
# ABAP: Codeblöcke und Kriterien
# ---------------------------------------------------------------------------
class TestAbap(unittest.TestCase):
    def test_aufgaben_datei_ist_gueltig(self):
        aufgaben = abap.lade_aufgaben()
        self.assertEqual(len(aufgaben), 7)
        for a in aufgaben:
            self.assertIn(a["dateityp"], {"prog", "clas", "ddls", "keiner"})
            self.assertTrue(a["kriterien"])

    def test_kriterien_modernisierung(self):
        aufgabe = next(a for a in abap.lade_aufgaben() if a["id"] == "modernisierung")
        antwort = (
            "Hier der Code:\n```abap\nSELECT * FROM scarr INTO TABLE @DATA(lt_tab).\n"
            "DATA(lv_name) = |Name: { lt_tab[ carrid = 'LH' ]-carrname }|.\nWRITE lv_name.\n```"
        )
        ergebnis = abap.pruefe_kriterien(aufgabe, antwort, abap.codebloecke(antwort))
        self.assertTrue(all(k["erfuellt"] for k in ergebnis), ergebnis)

    def test_verbotenes_muster(self):
        aufgabe = next(a for a in abap.lade_aufgaben() if a["id"] == "modernisierung")
        antwort = "```abap\nMOVE a TO b.\n```"
        ergebnis = {
            k["beschreibung"]: k["erfuellt"] for k in abap.pruefe_kriterien(aufgabe, antwort, abap.codebloecke(antwort))
        }
        self.assertFalse(ergebnis["kein MOVE mehr"])


if __name__ == "__main__":
    unittest.main()
