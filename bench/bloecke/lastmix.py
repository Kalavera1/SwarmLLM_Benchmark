"""Block lastmix: Wie viele Nutzer schafft das Modell, bevor es zu langsam wird?

Realistische Mischung wie im Projektziel (ca. 30 Nutzer):
  Coding-Agenten (4)   lange, wachsende Kontexte; jede Runde hängt eine neue
                       „Tool-Ausgabe“ an den Verlauf (Prefix-Cache wird genutzt)
  Chat-Nutzer (n)      kurze Fragen mit Denkpause dazwischen
Die Zahl der Chat-Nutzer steigt stufenweise. Jede Stufe läuft eine feste Zeit
und wird gegen Zielwerte (SLOs) bewertet:
  Chat: Zeit bis zum ersten Token p90 <= SLO_TTFT_P90_S
        Ausgabetempo pro Nutzer p10 >= SLO_MIN_TOK_S (auch die langsamsten 10 %)
  Agenten: Zeit bis zum ersten Token p90 <= SLO_AGENT_TTFT_P90_S
Ergebnis: die größte Nutzerzahl, bei der alle Ziele eingehalten werden.

In der Vollstufe kommt in der letzten Stufe ein sehr großer Prompt dazu
(Erfahrung B300: ein 500k-Prompt bremste parallele Chats auf ca. 30 %).
"""

from __future__ import annotations

import random
import threading
import time

from bench import statistik, texte

EBENE = "System"
BESCHREIBUNG = "Coding-Agenten plus Chat-Nutzer bis 30 gesamt, bewertet gegen Zielwerte"

CHAT_STUFEN = {"schnell": [8, 26], "voll": [4, 8, 16, 26]}
AGENTEN = 4
DAUER_S = {"schnell": 150, "voll": 480}
DENKPAUSE_S = (3.0, 15.0)
AGENT_START_TOKENS = 20_000
AGENT_ZUWACHS_TOKENS = 3_000
GROSSER_PROMPT_TOKENS = 400_000

STANDARD_SLO = {"SLO_TTFT_P90_S": 3.0, "SLO_MIN_TOK_S": 15.0, "SLO_AGENT_TTFT_P90_S": 20.0}


def slo(ctx) -> dict[str, float]:
    return {k: float(ctx.profil.get(k) or v) for k, v in STANDARD_SLO.items()}


# ---------------------------------------------------------------------------
# Nutzer-Schleifen; jede läuft in einem eigenen Thread bis zum Stopp-Signal
# ---------------------------------------------------------------------------
def chat_nutzer(ctx, nr: int, stopp: threading.Event, messungen: list) -> None:
    zufall = random.Random(nr)
    runde = 0
    while not stopp.is_set():
        runde += 1
        dokument = texte.fuelltext(1_500, seed=nr * 1000 + runde, zeichen_pro_token=ctx.zeichen_pro_token)
        frage = "Welche Komponente wird im Text am häufigsten genannt? Antworte in zwei bis drei Sätzen."
        antwort = ctx.client.chat(
            [{"role": "user", "content": dokument + "\n\n" + frage}], max_tokens=400, extra=ctx.denk_extra()
        )
        messungen.append(("chat", antwort))
        stopp.wait(zufall.uniform(*DENKPAUSE_S))


def coding_agent(ctx, nr: int, stopp: threading.Event, messungen: list, kontext_grenze: int) -> None:
    sitzung = 0
    while not stopp.is_set():
        sitzung += 1
        basis = texte.fuelltext(
            AGENT_START_TOKENS, seed=900_000 + nr * 100 + sitzung, zeichen_pro_token=ctx.zeichen_pro_token
        )
        verlauf = [{"role": "system", "content": "Du bist ein Coding-Agent. Projektdokumentation:\n" + basis}]
        tokens = AGENT_START_TOKENS
        runde = 0
        while not stopp.is_set() and tokens + AGENT_ZUWACHS_TOKENS < kontext_grenze:
            runde += 1
            ausgabe = texte.fuelltext(
                AGENT_ZUWACHS_TOKENS, seed=nr * 10_000 + sitzung * 100 + runde, zeichen_pro_token=ctx.zeichen_pro_token
            )
            verlauf.append(
                {
                    "role": "user",
                    "content": f"Tool-Ausgabe von Schritt {runde}:\n{ausgabe}\nWas ist der nächste Schritt?",
                }
            )
            antwort = ctx.client.chat(verlauf, max_tokens=800, extra=ctx.denk_extra())
            messungen.append(("agent", antwort))
            verlauf.append({"role": "assistant", "content": antwort.inhalt[:3000] or "(keine Antwort)"})
            tokens += AGENT_ZUWACHS_TOKENS + 800
            stopp.wait(1.0)


def grosser_prompt(ctx, stopp: threading.Event, messungen: list, laenge: int) -> None:
    stopp.wait(30)  # erst laufen lassen, dann stören
    if stopp.is_set():
        return
    text = texte.fuelltext(laenge, seed=777_777, zeichen_pro_token=ctx.zeichen_pro_token)
    antwort = ctx.client.chat(
        [{"role": "user", "content": text + "\n\nFasse in einem Satz zusammen."}], max_tokens=64, extra=ctx.denk_extra()
    )
    messungen.append(("gross", antwort))


# ---------------------------------------------------------------------------
# Eine Stufe: Threads starten, Zeit abwarten, stoppen, auswerten
# Gezählt werden nur Anfragen, die vor Ablauf der Zeit begonnen haben.
# ---------------------------------------------------------------------------
def stufe(ctx, chat: int, dauer: float, mit_grossem_prompt: bool, ziele: dict) -> dict:
    stopp = threading.Event()
    messungen: list = []
    grenze = min(int(ctx.max_kontext() * 0.7), 200_000)
    threads = [threading.Thread(target=chat_nutzer, args=(ctx, i, stopp, messungen), daemon=True) for i in range(chat)]
    threads += [
        threading.Thread(target=coding_agent, args=(ctx, i, stopp, messungen, grenze), daemon=True)
        for i in range(AGENTEN)
    ]
    gross = min(GROSSER_PROMPT_TOKENS, ctx.max_kontext() - 4_096)
    if mit_grossem_prompt:
        threads.append(threading.Thread(target=grosser_prompt, args=(ctx, stopp, messungen, gross), daemon=True))

    start = time.monotonic()
    for t in threads:
        t.start()
    stopp.wait(dauer)
    stopp.set()
    ende = start + dauer
    for t in threads:
        t.join(timeout=1800)

    gezaehlt = [(art, a) for art, a in messungen if a.start <= ende]
    for art, a in gezaehlt:
        ctx.merke(f"lastmix-{art}", a, chat_nutzer=chat)

    def auswahl(art: str) -> list:
        return [a for typ, a in gezaehlt if typ == art]

    chats, agenten = auswahl("chat"), auswahl("agent")
    ok_chats = [a for a in chats if a.ok]
    ok_agenten = [a for a in agenten if a.ok]
    chat_ttft = statistik.kennzahlen(a.ttft for a in ok_chats)
    chat_tempo = statistik.kennzahlen(a.decode_tok_s for a in ok_chats)
    agent_ttft = statistik.kennzahlen(a.ttft for a in ok_agenten)
    fehler = len(chats) - len(ok_chats) + len(agenten) - len(ok_agenten)

    eingehalten = {
        "chat_ttft": (chat_ttft.get("p90") is not None and chat_ttft["p90"] <= ziele["SLO_TTFT_P90_S"]),
        "chat_tempo": (chat_tempo.get("p10") is not None and chat_tempo["p10"] >= ziele["SLO_MIN_TOK_S"]),
        "agent_ttft": (agent_ttft.get("p90") is not None and agent_ttft["p90"] <= ziele["SLO_AGENT_TTFT_P90_S"]),
        "keine_fehler": fehler == 0,
    }
    ergebnis = {
        "nutzer_gesamt": chat + AGENTEN,
        "chat_nutzer": chat,
        "agenten": AGENTEN,
        "anfragen": {"chat": len(chats), "agent": len(agenten), "fehler": fehler},
        "chat_ttft_s": chat_ttft,
        "chat_tok_s": chat_tempo,
        "agent_ttft_s": agent_ttft,
        "agent_tok_s": statistik.kennzahlen(a.decode_tok_s for a in ok_agenten),
        "gesamt_tok_s": round(sum(a.ausgabe_tokens for _, a in gezaehlt if a.ok) / dauer, 1),
        "slo_eingehalten": eingehalten,
        "slo_ok": all(eingehalten.values()),
    }
    grosse = auswahl("gross")
    if grosse:
        ergebnis["grosser_prompt"] = {"tokens": gross, "ttft_s": grosse[0].ttft, "ok": grosse[0].ok}
    ctx.log(
        f"{chat + AGENTEN:>3} Nutzer: Chat TTFT p90 {chat_ttft.get('p90')} s, Chat tok/s p10 {chat_tempo.get('p10')}, "
        f"Agent TTFT p90 {agent_ttft.get('p90')} s, Fehler {fehler} "
        f"-> {'Ziele ok' if ergebnis['slo_ok'] else 'Ziele VERFEHLT'}"
    )
    return ergebnis


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------
def ausfuehren(ctx) -> dict:
    ziele = slo(ctx)
    ctx.log(f"Zielwerte: {ziele}")
    stufen_liste = CHAT_STUFEN[ctx.stufe]
    # Profil kann die Dauer kürzen, z. B. der Mock für einen schnellen Selbsttest
    dauer = float(ctx.profil.get("LASTMIX_DAUER_S") or DAUER_S[ctx.stufe])
    ergebnisse = []
    for nr, chat in enumerate(stufen_liste):
        letzte = nr == len(stufen_liste) - 1
        ergebnisse.append(stufe(ctx, chat, dauer, ctx.voll and letzte, ziele))

    erfuellt = [e["nutzer_gesamt"] for e in ergebnisse if e["slo_ok"]]
    max_nutzer = max(erfuellt) if erfuellt else 0
    return {
        "bestanden": max_nutzer >= 30,
        "kennzahlen": {"max_nutzer_mit_zielen": max_nutzer, "ziel_nutzer": 30},
        "zielwerte": ziele,
        "stufen": ergebnisse,
    }
