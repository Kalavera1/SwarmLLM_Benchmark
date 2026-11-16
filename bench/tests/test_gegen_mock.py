"""Integrationstest: Client und Blöcke gegen den echten Mock-Server.

Startet chat-stack/mock/mock_openai.py als Unterprozess auf einem freien Port (mit
API-Key, wie vLLM) und prüft Streaming, Tool-Calls, Key-Schutz und dass Blöcke
ein gültiges Ergebnis-JSON schreiben. Kein Netz nach außen, keine GPU.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from bench.ablauf import Kontext, fuehre_block_aus
from bench.bloecke import BLOECKE
from bench.client import Client
from bench.konfig import REPO, Profil, Ziel

MOCK = REPO / "chat-stack" / "mock" / "mock_openai.py"
KEY = "test-key-nur-fuer-unittests"  # gitleaks: kein echtes Secret


# ---------------------------------------------------------------------------
# Mock starten und stoppen (einmal für alle Tests der Klasse)
# ---------------------------------------------------------------------------
def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestGegenMock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = freier_port()
        umgebung = {**os.environ, "MOCK_API_KEY": KEY, "MOCK_DECODE_TOK_S": "5000", "MOCK_PREFILL_TOK_S": "1000000"}
        cls.prozess = subprocess.Popen(
            [sys.executable, str(MOCK), "--host", "127.0.0.1", "--port", str(cls.port)],
            env=umgebung,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cls.url = f"http://127.0.0.1:{cls.port}/v1"
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        cls.client = Client(cls.url, KEY, "mock-model", timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.prozess.terminate()
        cls.prozess.wait(timeout=10)

    # --- Client -------------------------------------------------------------
    def test_streaming_misst_zeiten(self):
        antwort = self.client.chat([{"role": "user", "content": "Hallo"}], max_tokens=32)
        self.assertTrue(antwort.ok, antwort.fehler)
        self.assertIsNotNone(antwort.ttft)
        self.assertGreater(antwort.ausgabe_tokens, 1)
        self.assertEqual(antwort.finish_reason, "stop")
        self.assertIsNotNone(antwort.decode_tok_s)

    def test_tool_call_wird_zusammengesetzt(self):
        tool = {"type": "function", "function": {"name": "f", "parameters": {"type": "object"}}}
        antwort = self.client.chat([{"role": "user", "content": "Nutze das tool"}], tools=[tool])
        self.assertEqual(antwort.tool_calls[0]["function"]["name"], "f")
        self.assertEqual(json.loads(antwort.tool_calls[0]["function"]["arguments"]), {"mock": True})

    def test_ohne_key_abgewiesen(self):
        status, _ = Client(self.url, "", "mock-model").get_json("/models", mit_key=False)
        self.assertEqual(status, 401)

    def test_metriken_fehlen_beim_mock(self):
        self.assertEqual(self.client.metriken(), {})

    # --- Blöcke -------------------------------------------------------------
    def test_bloecke_schreiben_gueltiges_json(self):
        profil = Profil("mock-test", {"SERVED_NAME": "mock-model", "MAX_MODEL_LEN": "262144", "VISION": "1"})
        ziel = Ziel(basis_url=self.url, api_key=KEY, modell="mock-model")
        ctx = Kontext(profil=profil, ziel=ziel, client=self.client, ausgabe=lambda _t: None)
        with tempfile.TemporaryDirectory() as ordner:
            for name in ("integration", "waechter", "agent", "bilder", "rechnen"):
                with self.subTest(block=name):
                    ergebnis = fuehre_block_aus(ctx, name, BLOECKE[name], ordner=Path(ordner))
                    self.assertNotIn("fehler", ergebnis)
                    self.assertIn("meta", ergebnis)
                    dateien = list((Path(ordner) / "mock-test" / name).glob("*.json"))
                    self.assertEqual(len(dateien), 1)
                    json.loads(dateien[0].read_text(encoding="utf-8"))
            # Key-Schutz muss beim echten Profil (KEY_PFLICHT Standard) bestehen
            integration = json.loads(next((Path(ordner) / "mock-test" / "integration").glob("*.json")).read_text())
            self.assertTrue(integration["pruefungen"]["key_schutz"]["bestanden"])
            self.assertTrue(integration["bestanden"])


if __name__ == "__main__":
    unittest.main()
