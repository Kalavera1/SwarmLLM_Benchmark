"""Testsuite für SwarmLLM_Benchmark (Phase 2).

Misst ein Modell hinter einer OpenAI-kompatiblen API (vLLM, LiteLLM oder den
Mock-Server) in einzeln startbaren Blöcken. Nur Python-Standardbibliothek, damit
die Suite auf jedem Steuerrechner ohne Installation läuft.

Aufruf: python3 -m bench --help
"""

VERSION = "1.0"
