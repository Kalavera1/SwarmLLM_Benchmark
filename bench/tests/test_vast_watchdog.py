"""Unit-Tests für server/vast-watchdog.sh gegen eine nachgebaute Vast-API.

Der Watchdog ist der Auto-Stopp auf Vast.ai (Regel 5): Nach Ablauf schickt er
DELETE /instances/<id> mit dem Instanz-Key. Die echte API wird nicht aufgerufen
(kostet Geld, braucht eine Instanz). Geprüft wird, dass die Anfrage richtig
ankommt, dass Neustellen den alten Watchdog ersetzt und dass der Key nicht in
der Prozessliste steht. Eine Minute dauert im Test eine Sekunde (WATCHDOG_TAKT_S).
"""

from __future__ import annotations

import contextlib
import http.server
import os
import signal
import subprocess
import threading
import time
import unittest
from pathlib import Path

from bench.konfig import REPO

SKRIPT = REPO / "server" / "vast-watchdog.sh"
# Feste Pfade, weil das Skript sie so nutzt (in der Instanz gibt es nur einen Nutzer)
PID_DATEI = Path("/tmp/swarmllm-watchdog.pid")  # noqa: S108
LOG = Path("/tmp/swarmllm-watchdog.log")  # noqa: S108
KEY = "instanz-key-nur-fuer-den-test"


# ---------------------------------------------------------------------------
# Nachgebaute Vast-API: merkt sich jede DELETE-Anfrage mit Pfad und Key
# ---------------------------------------------------------------------------
class _VastAttrappe(http.server.BaseHTTPRequestHandler):
    anfragen: list[tuple[str, str]] = []

    def do_DELETE(self):  # noqa: N802 (Name von http.server vorgegeben)
        self.anfragen.append((self.path, self.headers.get("Authorization", "")))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"success": true}')

    def log_message(self, *args):
        pass


# ---------------------------------------------------------------------------
# Watchdog starten, auf die Löschung warten, aufräumen
# ---------------------------------------------------------------------------
class TestVastWatchdog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), _VastAttrappe)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.api = f"http://127.0.0.1:{cls.server.server_address[1]}/api/v0"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        _VastAttrappe.anfragen = []
        LOG.unlink(missing_ok=True)

    def tearDown(self):
        # Einen noch laufenden Watchdog beenden, damit nichts liegen bleibt
        if PID_DATEI.exists():
            with contextlib.suppress(ProcessLookupError, ValueError):
                os.kill(int(PID_DATEI.read_text()), signal.SIGTERM)
            PID_DATEI.unlink(missing_ok=True)

    def starte(self, *argumente: str, mit_vast: bool = True) -> subprocess.CompletedProcess:
        umgebung = {k: v for k, v in os.environ.items() if not k.startswith("CONTAINER_")}
        umgebung.update(VAST_API=self.api, WATCHDOG_TAKT_S="1")
        if mit_vast:
            umgebung.update(CONTAINER_ID="4242", CONTAINER_API_KEY=KEY)
        befehl = ["bash", str(SKRIPT), *argumente]
        return subprocess.run(befehl, env=umgebung, capture_output=True, text=True, timeout=30)

    def warte_auf_anfrage(self, sekunden: float = 10) -> None:
        ende = time.time() + sekunden
        while not _VastAttrappe.anfragen and time.time() < ende:
            time.sleep(0.2)

    def test_loescht_nach_ablauf_mit_instanz_key(self):
        ergebnis = self.starte("1")
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stderr)
        self.warte_auf_anfrage()
        self.assertEqual(_VastAttrappe.anfragen, [("/api/v0/instances/4242", f"Bearer {KEY}")])
        time.sleep(0.5)
        self.assertIn("Löschung angefordert: HTTP 200", LOG.read_text())

    def test_neu_stellen_ersetzt_den_alten_watchdog(self):
        # Alter Watchdog: 3 s. Würde er nicht beendet, käme eine zweite Löschung an.
        self.assertEqual(self.starte("3").returncode, 0)
        status = self.starte("status")
        self.assertEqual(status.returncode, 0)
        self.assertIn('"minuten": 3', status.stdout)
        # Der Key darf nicht in der Prozessliste stehen (nur in der Umgebung)
        prozesse = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
        self.assertNotIn(KEY, prozesse)

        neu = self.starte("1")
        self.assertIn("Bisherigen Watchdog beendet", neu.stdout)
        self.warte_auf_anfrage()
        time.sleep(3.5)  # länger als die 3 s des alten Watchdogs
        self.assertEqual(len(_VastAttrappe.anfragen), 1)

    def test_ohne_vast_instanz_kein_start(self):
        ergebnis = self.starte("1", mit_vast=False)
        self.assertEqual(ergebnis.returncode, 1)
        self.assertIn("CONTAINER_ID oder CONTAINER_API_KEY fehlt", ergebnis.stderr)

    def test_minuten_muessen_zahl_sein(self):
        ergebnis = self.starte("bald")
        self.assertEqual(ergebnis.returncode, 1)
        self.assertIn("ganze Zahl", ergebnis.stderr)


if __name__ == "__main__":
    unittest.main()
