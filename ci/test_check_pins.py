"""Unit-Tests für ci/check_pins.py (unterste Ebene des V-Modells).

Selbsttest des Pin-Prüfers: Jeder Test füttert die Prüffunktion mit einer
künstlichen Zeile, deren richtiges Ergebnis feststeht. Erst wenn diese Tests
grün sind, kann man der echten Pin-Prüfung über das Repo trauen.

Aufruf: python3 -m unittest discover -s ci -v
"""

import unittest

from check_pins import pruefe_zeilen

# ---------------------------------------------------------------------------
# Testdaten und Hilfsfunktion
#
# DIGEST und SHA sind Dummy-Werte im richtigen Format (64 bzw. 40 Hex-Zeichen).
# Ob der Hash echt ist, spielt keine Rolle – der Prüfer prüft nur das Format.
#
# meldungen() liefert die Liste der Fehlermeldungen für eine Datei und ihren
# Text: leere Liste = in Ordnung, ein Eintrag = ein Verstoß.
# ---------------------------------------------------------------------------
DIGEST = "sha256:" + "a" * 64
SHA = "b" * 40


def meldungen(datei: str, text: str) -> list[str]:
    return [v.text for v in pruefe_zeilen(datei, text.splitlines())]


# ---------------------------------------------------------------------------
# Images in YAML-Dateien (z. B. local/stack.yml)
#
# Durchgehen darf nur ein Image mit @sha256-Digest. Ein Tag allein (auch
# "latest") ist ein Verstoß. Erlaubt bleiben Variablen wie ${LITELLM_IMAGE}
# (Wert wird an anderer Stelle geprüft), auskommentierte Zeilen und Zeilen
# mit dem Marker "pin-check: ignore".
# ---------------------------------------------------------------------------
class ImagesInYaml(unittest.TestCase):
    def test_digest_ist_ok(self):
        self.assertEqual(meldungen("local/stack.yml", f"    image: ghcr.io/x/y:1.0@{DIGEST}"), [])

    def test_tag_ohne_digest_ist_verstoss(self):
        self.assertEqual(len(meldungen("local/stack.yml", "    image: ghcr.io/x/y:1.0")), 1)

    def test_latest_ist_verstoss(self):
        self.assertEqual(len(meldungen("local/stack.yml", "image: 'nginx:latest'")), 1)

    def test_variable_wird_uebersprungen(self):
        self.assertEqual(meldungen("local/stack.yml", "    image: ${LITELLM_IMAGE}"), [])

    def test_kommentar_wird_uebersprungen(self):
        self.assertEqual(meldungen("local/stack.yml", "    # image: nginx:latest"), [])

    def test_ignore_marker(self):
        self.assertEqual(meldungen("local/stack.yml", "image: nginx:latest  # pin-check: ignore"), [])


# ---------------------------------------------------------------------------
# Images in Variablen (Shell-Skripte, .env-Dateien)
#
# Jede Variable, deren Name auf IMAGE endet (IMAGE=, VLLM_IMAGE=, auch mit
# "export"), braucht einen Digest. Ein leerer Wert ist erlaubt – so sieht
# z. B. local/images.env aus, bevor der Digest eingetragen ist.
# ---------------------------------------------------------------------------
class ImagesInVariablen(unittest.TestCase):
    def test_image_variable_mit_digest(self):
        self.assertEqual(meldungen("profiles/ds4/pod.env", f"IMAGE=ghcr.io/a/vllm@{DIGEST}"), [])

    def test_image_variable_ohne_digest(self):
        self.assertEqual(len(meldungen("profiles/ds4/pod.env", "VLLM_IMAGE=ghcr.io/a/vllm:karmic-kraken-beta")), 1)

    def test_export_wird_erkannt(self):
        self.assertEqual(len(meldungen("runpod/start.sh", 'export IMAGE="ghcr.io/a/vllm:beta"')), 1)

    def test_leerer_wert_ist_ok(self):
        self.assertEqual(meldungen("runpod/start.sh", "IMAGE="), [])


# ---------------------------------------------------------------------------
# GitHub Actions in Workflows
#
# "uses: owner/repo@..." muss auf einen vollen Commit-SHA zeigen. Ein Tag wie
# @v7 kann der Action-Autor jederzeit auf anderen Code umbiegen. Lokale
# Actions (./…) haben keine Version und sind erlaubt.
# ---------------------------------------------------------------------------
class ActionsPins(unittest.TestCase):
    def test_commit_sha_ist_ok(self):
        self.assertEqual(meldungen(".github/workflows/ci.yml", f"      - uses: actions/checkout@{SHA} # v7"), [])

    def test_tag_ist_verstoss(self):
        self.assertEqual(len(meldungen(".github/workflows/ci.yml", "      - uses: actions/checkout@v7")), 1)

    def test_lokale_action_ist_ok(self):
        self.assertEqual(meldungen(".github/workflows/ci.yml", "      - uses: ./.github/actions/x"), [])


# ---------------------------------------------------------------------------
# Modell-Profile (profiles/**/*.env)
#
# Wer MODEL_ID setzt, muss MODEL_REVISION als vollen Commit-Hash setzen.
# Ein Branch-Name wie "main" wandert und ist deshalb ein Verstoß. Außerhalb
# von profiles/ wird diese Regel nicht angewendet.
# ---------------------------------------------------------------------------
class ModellProfile(unittest.TestCase):
    def test_id_mit_revision(self):
        text = f"MODEL_ID=deepseek-ai/DeepSeek-V4-Flash\nMODEL_REVISION={SHA}"
        self.assertEqual(meldungen("profiles/ds4/model.env", text), [])

    def test_id_ohne_revision(self):
        self.assertEqual(
            meldungen("profiles/ds4/model.env", "MODEL_ID=deepseek-ai/DeepSeek-V4-Flash"),
            ["MODEL_ID ohne MODEL_REVISION"],
        )

    def test_revision_als_branch(self):
        text = "MODEL_ID=deepseek-ai/DeepSeek-V4-Flash\nMODEL_REVISION=main"
        self.assertEqual(len(meldungen("profiles/ds4/model.env", text)), 1)

    def test_ausserhalb_von_profiles_nicht_geprueft(self):
        self.assertEqual(meldungen("local/test.env", "MODEL_ID=x/y"), [])


if __name__ == "__main__":
    unittest.main()
