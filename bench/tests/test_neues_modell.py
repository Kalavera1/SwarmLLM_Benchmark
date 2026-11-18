"""Unit-Tests für profiles/neu.py und profiles/wache.py ohne Netz.

Hugging Face wird nachgestellt: neu.hf_json bekommt feste Antworten. Geprüft
werden die Vorprüfung (passt das Modell auf 2× 96 GB?), das erzeugte Profil
(Entwurf, nichts gepinnt, Pin-Prüfung der CI besteht) und die Modell-Wache
(meldet nur Neues).
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from bench.konfig import REPO, Profil, lies_env_datei

sys.path.insert(0, str(REPO / "profiles"))
import neu  # noqa: E402 (Pfad muss vorher gesetzt sein)
import wache  # noqa: E402

# Pin-Prüfung der CI über den Pfad laden (ci/ ist kein Paket)
_spec = importlib.util.spec_from_file_location("check_pins", REPO / "ci" / "check_pins.py")
check_pins = importlib.util.module_from_spec(_spec)
sys.modules["check_pins"] = check_pins  # dataclasses brauchen das Modul in sys.modules
_spec.loader.exec_module(check_pins)


# ---------------------------------------------------------------------------
# Nachgestelltes Hugging Face: zwei Modelle und eine Suche
# ---------------------------------------------------------------------------
GB = 10**9
ANTWORTEN = {
    # Bildfähiges Modell mit 54 GB Gewichten und 1M Kontext
    "/api/models/Org/Bild-27B/revision/main?blobs=true": {
        "sha": "a" * 40,
        "pipeline_tag": "image-text-to-text",
        "siblings": [
            {"rfilename": "model-00001.safetensors", "size": 30 * GB},
            {"rfilename": "model-00002.safetensors", "size": 24 * GB},
            {"rfilename": "config.json", "size": 5000},
        ],
    },
    "/Org/Bild-27B/resolve/main/config.json": {"text_config": {"max_position_embeddings": 1048576}},
    # Reines GGUF-Repo mit zwei Quantisierungen, ohne config.json
    "/api/models/Org/Riese-GGUF/revision/main?blobs=true": {
        "sha": "b" * 40,
        "pipeline_tag": "text-generation",
        "siblings": [
            {"rfilename": "Q3/riese-00001.gguf", "size": 343 * GB},
            {"rfilename": "Q8/riese-00001.gguf", "size": 800 * GB},
        ],
    },
    # Suche der Modell-Wache
    "/api/models?author=Org&search=Neu": [
        {"id": "Org/Bild-27B", "createdAt": "2026-11-20T08:00:00.000Z"},
        {"id": "Org/Schon-Gemeldet", "createdAt": "2026-11-19T08:00:00.000Z"},
    ],
}


def falsches_hf(url: str, token: str = ""):
    pfad = url.removeprefix("https://huggingface.co")
    pfad = pfad.split("&sort=")[0] if pfad.startswith("/api/models?") else pfad
    if pfad in ANTWORTEN:
        return ANTWORTEN[pfad]
    raise urllib.error.HTTPError(url, 404, "nicht gefunden", {}, None)


# ---------------------------------------------------------------------------
# Vorprüfung: Größe, Platz, Bilder, Kontext
# ---------------------------------------------------------------------------
class TestVorpruefung(unittest.TestCase):
    def test_platz_stufen(self):
        self.assertEqual(neu.bewerte_platz(54)[0], "passt")
        self.assertEqual(neu.bewerte_platz(170)[0], "knapp")
        stufe, text, ram = neu.bewerte_platz(343)
        self.assertEqual((stufe, ram), ("auslagern", 263))  # 343 − 0,75 × 192 + 64
        self.assertIn("Arbeitsspeicher", text)
        self.assertEqual(neu.bewerte_platz(1200)[0], "zu-gross")
        self.assertEqual(neu.bewerte_platz(0)[0], "unklar")

    def test_gewichte_mit_auswahl(self):
        siblings = ANTWORTEN["/api/models/Org/Riese-GGUF/revision/main?blobs=true"]["siblings"]
        self.assertEqual(neu.gewichte_gb(siblings), 1143.0)
        self.assertEqual(neu.gewichte_gb(siblings, "Q3/"), 343.0)

    def test_bilder_erkennen(self):
        self.assertTrue(neu.bildfaehig({"pipeline_tag": "image-text-to-text"}, {})[0])
        self.assertTrue(neu.bildfaehig({}, {"vision_config": {}})[0])
        self.assertFalse(neu.bildfaehig({"pipeline_tag": "text-generation"}, {"model_type": "x"})[0])
        self.assertIsNone(neu.bildfaehig({}, {})[0])

    def test_kontext(self):
        self.assertEqual(neu.kontext({"max_position_embeddings": 262144}), 262144)
        self.assertEqual(neu.kontext({"text_config": {"max_position_embeddings": 4096}}), 4096)
        self.assertIsNone(neu.kontext({}))


# ---------------------------------------------------------------------------
# Profil anlegen: in einem Zeitordner statt in profiles/
# ---------------------------------------------------------------------------
class TestNeuesProfil(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "profiles" / "qwen38-27b", self.ordner / "qwen38-27b")
        # Vorbild wie nach pin.py: gepinnte Felder müssen im neuen Profil wieder fehlen
        vorbild = self.ordner / "qwen38-27b" / "profile.env"
        gepinnt = f"\n# Gepinnt am 2026-11-17 mit profiles/pin.py\nMODEL_ID=nvidia/X\nMODEL_REVISION={'c' * 40}\n"
        vorbild.write_text(vorbild.read_text(encoding="utf-8") + gepinnt + "MODELL_GROESSE_GB=29.0\n", encoding="utf-8")
        self.patches = [
            mock.patch.object(neu, "PROFILE_ORDNER", self.ordner),
            mock.patch.object(neu, "REPO", self.ordner),
            mock.patch.object(neu, "hf_json", falsches_hf),
            mock.patch.object(neu, "lies_einstellungen", lambda: {}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.ordner)

    def lade(self, name: str) -> tuple[str, dict]:
        datei = self.ordner / name / "profile.env"
        return datei.read_text(encoding="utf-8"), lies_env_datei(datei)

    def assert_pins_ok(self, name: str, text: str):
        verstoesse = check_pins.pruefe_zeilen(f"profiles/{name}/profile.env", text.splitlines())
        self.assertEqual(verstoesse, [])

    def test_aus_vorlage(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(neu.main(["bild-27b", "--quelle", "Org/Bild-27B"]), 0)
        text, werte = self.lade("bild-27b")
        self.assertEqual(werte["PROFIL_STATUS"], "entwurf")
        self.assertEqual(werte["MODEL_QUELLE"], "Org/Bild-27B")
        self.assertEqual(werte["VISION"], "1")
        self.assertEqual(werte["MAX_MODEL_LEN"], "524288")  # 1M nativ, gekappt auf den 500k-Punkt
        self.assertEqual(werte["DISK_GB"], "85")  # 54 × 1,2 + 20, aufgerundet
        self.assertIn("passt in den VRAM", text)
        self.assertTrue(Profil("bild-27b", werte).get("SERVED_NAME"))
        self.assert_pins_ok("bild-27b", text)

    def test_nach_vorbild(self):
        argumente = ["riese-q3", "--quelle", "Org/Riese-GGUF", "--wie", "qwen38-27b", "--auswahl", "Q3/"]
        with mock.patch("sys.stdout"):
            self.assertEqual(neu.main(argumente), 0)
        text, werte = self.lade("riese-q3")
        vorbild = lies_env_datei(self.ordner / "qwen38-27b" / "profile.env")
        # Startparameter aus dem Vorbild, aber neues Modell und nichts gepinnt
        self.assertEqual(werte["VLLM_IMAGE_QUELLE"], vorbild["VLLM_IMAGE_QUELLE"])
        self.assertEqual(werte["MODEL_QUELLE"], "Org/Riese-GGUF")
        self.assertEqual(werte["SERVED_NAME"], "riese-q3")
        self.assertEqual(werte["PROFIL_STATUS"], "entwurf")
        self.assertEqual(werte["VLLM_IMAGE"], "")
        for feld in ("MODEL_ID", "MODEL_REVISION", "MODELL_GROESSE_GB"):
            self.assertNotIn(feld, werte)
        self.assertNotIn("Gepinnt am", text)
        self.assertEqual(werte["VISION"], "0")
        self.assertEqual(werte["HOST_RAM_MIN_GB"], "263")
        self.assertIn("profiles/pin.py riese-q3", text)
        self.assertNotIn("Qwen3.8-27B (dense", text)  # Kopfkommentar des Vorbilds ist weg
        self.assertIn("nur Dateien mit 'Q3/'", text)
        self.assert_pins_ok("riese-q3", text)

    def test_trocken_schreibt_nichts(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(neu.main(["bild-27b", "--quelle", "Org/Bild-27B", "--trocken"]), 0)
        self.assertFalse((self.ordner / "bild-27b").exists())

    def test_verweigert_vorhandenes_profil_und_falschen_namen(self):
        with mock.patch("sys.stderr"):
            self.assertEqual(neu.main(["qwen38-27b", "--quelle", "Org/Bild-27B"]), 1)
            self.assertEqual(neu.main(["Gross_Buchstaben", "--quelle", "Org/Bild-27B"]), 1)

    def test_unbekanntes_repo(self):
        with mock.patch("sys.stderr") as fehler:
            self.assertEqual(neu.main(["gibts-nicht", "--quelle", "Org/Gibts-Nicht"]), 1)
        self.assertIn("HTTP 404", "".join(str(c) for c in fehler.write.call_args_list))


# ---------------------------------------------------------------------------
# Modell-Wache: meldet nur, was weder in Profilen noch in alten Issues steht
# ---------------------------------------------------------------------------
class TestWache(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp())
        self.patches = [
            mock.patch.object(neu, "PROFILE_ORDNER", self.ordner),
            mock.patch.object(neu, "hf_json", falsches_hf),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.ordner)

    def test_liste_lesen(self):
        datei = self.ordner / "liste.txt"
        datei.write_text("# Kommentar\nQwen Qwen4   # warum\n\nnvidia Qwen4\n", encoding="utf-8")
        self.assertEqual(wache.lies_liste(datei), [("Qwen", "Qwen4"), ("nvidia", "Qwen4")])

    def test_echte_liste_ist_lesbar(self):
        self.assertIn(("Qwen", "Qwen4"), wache.lies_liste())

    def test_meldet_nur_neues(self):
        funde = wache.finde_neue([("Org", "Neu")], alte_meldungen="| [Org/Schon-Gemeldet](…) |")
        self.assertEqual([f["repo"] for f in funde], ["Org/Bild-27B"])
        self.assertEqual(funde[0]["gb"], 54.0)

    def test_repo_im_profil_ist_bekannt(self):
        (self.ordner / "bild").mkdir()
        (self.ordner / "bild" / "profile.env").write_text("MODEL_QUELLE=Org/Bild-27B\n", encoding="utf-8")
        funde = wache.finde_neue([("Org", "Neu")], alte_meldungen="Org/Schon-Gemeldet")
        self.assertEqual(funde, [])

    def test_markdown_nur_bei_funden(self):
        ziel = self.ordner / "funde.md"
        with mock.patch.object(wache, "lies_liste", lambda: [("Org", "Neu")]), mock.patch("sys.stdout"):
            self.assertEqual(wache.main(["--markdown", str(ziel)]), 0)
        text = ziel.read_text(encoding="utf-8")
        self.assertIn("[Org/Bild-27B](https://huggingface.co/Org/Bild-27B)", text)
        self.assertIn("profiles/neu.py", text)

        ziel.unlink()
        bekannt = self.ordner / "bekannt.txt"
        bekannt.write_text("Org/Bild-27B Org/Schon-Gemeldet", encoding="utf-8")
        with mock.patch.object(wache, "lies_liste", lambda: [("Org", "Neu")]), mock.patch("sys.stdout"):
            self.assertEqual(wache.main(["--bekannt", str(bekannt), "--markdown", str(ziel)]), 0)
        self.assertFalse(ziel.exists())


if __name__ == "__main__":
    unittest.main()
