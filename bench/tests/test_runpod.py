"""Unit-Tests für runpod/rp.py ohne RunPod-API: Profilprüfung, Ports, Kostenbuch.

Die API selbst wird nicht aufgerufen (kostet Geld, braucht Key). Geprüft wird
die Logik drumherum, die über Geld entscheidet.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bench.konfig import REPO, Profil, lade_profil

# runpod/ ist kein Paket; Modul über den Pfad laden
_spec = importlib.util.spec_from_file_location("rp", REPO / "runpod" / "rp.py")
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)


# ---------------------------------------------------------------------------
# Nur gepinnte, freigegebene Profile dürfen starten
# ---------------------------------------------------------------------------
class TestProfilpruefung(unittest.TestCase):
    def test_ungepinnt_wird_abgelehnt(self):
        probleme = rp.pruefe_profil(lade_profil("qwen38-27b"))
        self.assertTrue(any("nicht gepinnt" in p for p in probleme))

    def test_entwurf_wird_abgelehnt(self):
        probleme = rp.pruefe_profil(lade_profil("deepseek-v41-flash"))
        self.assertTrue(any("entwurf" in p for p in probleme))

    def test_gepinnt_ist_ok(self):
        profil = Profil(
            "x",
            {"MODEL_ID": "a/b", "MODEL_REVISION": "0" * 40, "VLLM_IMAGE": "vllm/vllm-openai@sha256:" + "a" * 64},
        )
        self.assertEqual(rp.pruefe_profil(profil), [])


# ---------------------------------------------------------------------------
# Öffentliche Adresse aus runtime.ports
# ---------------------------------------------------------------------------
class TestPorts(unittest.TestCase):
    def test_adresse(self):
        pod = {"runtime": {"ports": [{"private": 8000, "public": 40123, "ip": "1.2.3.4", "type": "tcp"}]}}
        self.assertEqual(rp.oeffentliche_adresse(pod, 8000), "http://1.2.3.4:40123")
        self.assertIsNone(rp.oeffentliche_adresse(pod, 8001))
        self.assertIsNone(rp.oeffentliche_adresse({"runtime": None}, 8000))


# ---------------------------------------------------------------------------
# Kostenbuch: verbuchen und aufsummieren
# ---------------------------------------------------------------------------
class TestKosten(unittest.TestCase):
    def test_kein_budget_mehr(self):
        self.assertFalse(hasattr(rp, "budget"))

    def test_verbuchen_und_summe(self):
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / "kosten.csv"
            with mock.patch.object(rp, "KOSTEN_DATEI", datei):
                self.assertEqual(rp.verbraucht(), 0.0)
                rp.verbuche({"pod_id": "a", "kosten_usd": "1.500"})
                rp.verbuche({"pod_id": "b", "kosten_usd": "2.250"})
                self.assertAlmostEqual(rp.verbraucht(), 3.75)

    def test_minuten_seit(self):
        self.assertAlmostEqual(rp.minuten_seit(None, ersatz=rp.time.time() - 600), 10, delta=0.1)
        self.assertGreater(rp.minuten_seit("2026-01-01T00:00:00Z", ersatz=0), 0)


# ---------------------------------------------------------------------------
# pin.py: Image-Referenzen zerlegen und Registry-Adressen bilden
# ---------------------------------------------------------------------------
_pin_spec = importlib.util.spec_from_file_location("pin", REPO / "profiles" / "pin.py")
pin = importlib.util.module_from_spec(_pin_spec)
_pin_spec.loader.exec_module(pin)


class TestPinImage(unittest.TestCase):
    def test_zerlegen(self):
        faelle = {
            "vllm/vllm-openai:v0.30.0": ("docker.io", "vllm/vllm-openai", "v0.30.0", "vllm/vllm-openai"),
            "nginx": ("docker.io", "library/nginx", "latest", "nginx"),
            "ghcr.io/local-inference-lab/vllm:release-10152026": (
                "ghcr.io",
                "local-inference-lab/vllm",
                "release-10152026",
                "ghcr.io/local-inference-lab/vllm",
            ),
            "localhost:5000/x/y": ("localhost:5000", "x/y", "latest", "localhost:5000/x/y"),
        }
        for ref, erwartet in faelle.items():
            with self.subTest(ref=ref):
                self.assertEqual(pin.zerlege_image(ref), erwartet)

    def test_registry_urls(self):
        token, manifest = pin.registry_urls("docker.io", "vllm/vllm-openai", "v0.30.0")
        self.assertIn("auth.docker.io", token)
        self.assertEqual(manifest, "https://registry-1.docker.io/v2/vllm/vllm-openai/manifests/v0.30.0")
        token, manifest = pin.registry_urls("ghcr.io", "a/b", "t")
        self.assertEqual(token, "https://ghcr.io/token?scope=repository:a/b:pull")
        self.assertEqual(manifest, "https://ghcr.io/v2/a/b/manifests/t")


if __name__ == "__main__":
    unittest.main()
