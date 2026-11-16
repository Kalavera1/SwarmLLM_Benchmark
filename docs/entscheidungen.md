# Entscheidungslog

Kurz festgehalten: was entschieden wurde, warum, und wo es herkommt. Neue Einträge oben.

---

## 2026-11-16 – DeepSeek V4.1 Flash ist das wichtigste Modell, Weg noch offen

**Entscheidung:** DeepSeek V4.1 Flash (763B, Bilder, 1M Kontext) wird getestet. Offen ist, auf welchem Weg:

| Weg | Hardware | Vorteil | Nachteil |
|---|---|---|---|
| A: Rezept theogravity | 2× RTX PRO 6000 (Zielhardware) | 512k Kontext, ≈ 250 tok/s bei einem Nutzer, 41,6 s bis zum ersten Token bei 505k (Angaben des Autors) | ein Autor, eine Maschine; gepatchtes vLLM, eigene Images müssen gebaut werden; Tempo hängt an CPU, RAM (≥ 128 GiB empfohlen) und NVMe des Hosts – bei RunPod-Community-Hosts nicht planbar |
| B: Karmic Kraken `ds41-flash` | 4× RTX PRO 6000 | fertiges Image, Bilder verifiziert, ≈ 249 tok/s bei einem Nutzer (rtx6kpro-Wiki) | misst nicht die Zielhardware; ≈ 6,56 $/h |

**Warum nicht einfach quantisieren:** Selbst mit 3 Bit sind es ≈ 322 GiB Gewichte, also deutlich mehr als 192 GB VRAM.

**Quellen:** [theogravity/deepseek-flash-v4.1-dual-rtx-6000](https://github.com/theogravity/deepseek-flash-v4.1-dual-rtx-6000), [rtx6kpro: DeepSeek V4.1 Flash](https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash.md)

## 2026-11-16 – Geldschonend: Community Cloud ohne Network Volume

**Entscheidung:** GPU-Pods laufen standardmäßig in der **Community Cloud**. Es gibt **kein Network Volume**; die Gewichte lädt jeder Pod beim Start auf seine Container-Disk. Alle Testblöcke eines Modells laufen in **einem** Pod am Stück. Ein Budget in `.env` (`RUNPOD_BUDGET_USD`) begrenzt die Summe aller Läufe.

**Warum:**
- Preis pro Karte und Stunde (on-demand, Stand 15.11.2026): Community 1,64 $, Secure 2,69 $. Für 2 Karten 3,28 $/h gegen 5,38 $/h.
- Network Volumes gibt es bei RunPod **nur in der Secure Cloud** und kosten 0,07 $/GB/Monat, auch ohne laufenden Pod. 600 GB für alle Modelle wären ca. 42 $/Monat.
- Ein Download von ca. 30–190 GB beim Start kostet in der Community Cloud nur wenige Minuten GPU-Zeit. Bei geschätzt 6–8 Pod-Starts ist das günstiger als Volume plus Secure-Aufpreis.
- Jeder Kaltstart (Laden, JIT, Autotuning) kostet 10–20 Minuten. Deshalb ein Pod pro Modell, nicht pro Block.

**Folgen:** Phase 3 (Network Volume vorbefüllen) entfällt. Die Secure Cloud mit Volume bleibt als Option im Skript, falls Community-Hosts kein P2P bieten.

**Risiko:** Community-Hosts sind unterschiedlich gut, P2P zwischen den Karten klappt nicht überall. Der Pod-Check verwirft solche Hosts nach wenigen Minuten.

**Quellen:** [computeprices.com, RunPod RTX PRO 6000](https://computeprices.com/providers/runpod/gpus/rtx-pro-6000), [RunPod-Doku Network Volumes](https://docs.runpod.io/storage/network-volumes)

## 2026-11-16 – RunPod REST-API v2

**Entscheidung:** Die Skripte nutzen `https://api.runpod.io/v2`.

**Warum:** Die v1-API (`rest.runpod.io/v1`) ist laut RunPod zum 15.11.2026 abgeschaltet. In v2 heißen Felder anders (`gpu: {id, count}` statt `gpuTypeIds`, `cloud` statt `cloudType`, Standard ist `SECURE`), und es gibt kein Feld für eine maximale Laufzeit – der Watchdog bleibt also unsere Aufgabe.

**Quelle:** [RunPod: Migrate from v1](https://docs.runpod.io/api-reference-v2/migrate-from-v1), [Create a Pod](https://docs.runpod.io/api-reference-v2/pods/create-a-pod)

## 2026-11-16 – Neue Modellauswahl: Bilder, Agenten, Kosten

**Entscheidung:** Testreihenfolge (siehe [README](../README.md#modell-kandidaten)):

0. **Qwen3.8-27B** als Referenz und für den ersten GPU-Test
1. **Qwen3.8-Flash-Next** (FP8, N-gram-Tabelle im Host-RAM)
2. **GLM-5.3-Flash** als `nvidia/GLM-5.3-Flash-FP4-Local`
3. DeepSeek V4 Flash und GLM über die Purtell-Runtime nur bei Restbudget

**Warum:**
- **Bilder und Agenten sind neue Anforderungen.** DeepSeek V4 Flash kann nur Text. Die Bild-Variante DeepSeek-V4-Flash-Vision-Exp braucht laut vLLM-Recipe ca. 202 GB VRAM und gilt auf 2 Karten als nicht unterstützt.
- **Qwen3.8-27B zuerst:** offizielles vLLM-Recipe für die RTX Pro 6000, nur ca. 29 GB Download, läuft auf einer Karte. Damit lässt sich die ganze Kette (Pod, Check, Testsuite) für wenig Geld prüfen, bevor ein großes Modell Stunden kostet. Danach dient es als Referenz: Ist ein großes Modell schlecht, zeigt der Vergleich, ob es am Modell oder an der Umgebung liegt.
- **Qwen3.8-Flash-Next:** unabhängig gemessen auf 2× RTX PRO 6000 ca. 146 tok/s mit MTP bei 512k Kontext (stondo), läuft mit Upstream-vLLM ohne Spezial-Runtime.
- **GLM-5.3-Flash FP4-Local:** NVIDIA hat genau diese Hardware validiert (ca. 166 GiB, 1,8 Mio. Token FP8-KV-Cache). Laut Z.ai die besten Agenten-Werte unter den Kandidaten (Herstellerangaben). Ein Community-Test meldete auf SM120 Endlosschleifen in der Ausgabe – deshalb gibt es jetzt den Qualitäts-Wächter in der Testsuite.
- **Purtell-EXL3 wird nicht gestrichen**, aber nachrangig: Das Ziel ist ausdrücklich vLLM, und der NVIDIA-Checkpoint läuft in einem vLLM-Container.

**Herstellerangaben vs. Messung:** Die Agenten-Benchmarks (Terminal-Bench, SWE-bench, Toolathlon) stammen fast alle von den Herstellern. Entschieden wird nach unseren eigenen Messungen.

**Quellen:** [vLLM Recipes](https://recipes.vllm.ai/browse), [nvidia/GLM-5.3-Flash-FP4-Local](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local), [stondo: Qwen3.8-Flash-Next auf 2× RTX PRO 6000](https://stondo.github.io/posts/qwen38-flash-next-512k-two-rtx-pro-6000/), [Qwen3.8-27B Recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B), [DeepSeek-V4-Flash-Vision-Exp Recipe](https://recipes.vllm.ai/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp)

## 2026-11-16 – Testsuite misst gegen Ziele (SLOs), nicht nur Durchsatz

**Entscheidung:** Der Lastmix steigt bis 30 Nutzer und wird gegen feste Zielwerte bewertet: Zeit bis zum ersten Token im Chat (p90) und Ausgabetempo pro Nutzer. Ergebnis ist die größte Nutzerzahl, bei der die Ziele noch eingehalten werden. Neu dazu kommen die Blöcke Bilder, Agentenschleife und Qualitäts-Wächter.

**Warum:** Die eigentliche Frage ist „Wie viele Nutzer schafft das Modell, bevor es zu langsam wird?“. Reine Durchsatzzahlen beantworten das nicht. Spekulatives Decoding wird mit natürlichen Texten gemessen, nicht mit Zufallstokens, sonst sind die Akzeptanzraten unrealistisch.

## 2026-11-01 – Testsuite nach V-Modell, ABAP als automatisch geprüfter Eval

**Entscheidung:** Die Tests werden in vier Ebenen gegliedert (Unit, Integration, System, Abnahme) und über eine Kommandozeile blockweise gestartet. Die Modellqualität bei ABAP wird als eigener Eval-Block gemessen: Codeblöcke werden mit abaplint geprüft, dazu kommt eine feste Kriterienliste je Aufgabe.

**Warum:**
- Jeder Block muss einzeln wiederholbar sein, damit nach einer Änderung nicht der ganze, teure GPU-Lauf neu nötig ist.
- Im B300-Test wurde ABAP nur durch Lesen bewertet und nicht kompiliert. Ein SAP-System steht privat nicht zur Verfügung; abaplint prüft die Syntax ohne SAP-System.

**Offen:** Wie weit abaplint CDS, Behavior Definitions (RAP) und SQLScript in AMDP abdeckt. Was nicht abgedeckt ist, bewertet die Kriterienliste.

## 2026-11-01 – Schlanke CI statt vollem Toolset

**Entscheidung:** GitHub Actions mit Secret-Scan (gitleaks), Pin-Prüfung und Linter (ruff, shellcheck). Actions und gitleaks sind per Commit-SHA bzw. Prüfsumme gepinnt. Kein Dependabot.

**Warum:**
- Ein geleakter RunPod-Key kostet echtes Geld; der Secret-Scan läuft deshalb über die gesamte Historie, mit einer eigenen Regel für die Variablen aus `.env.example`.
- Regel 4 (Alles gepinnt) wird technisch erzwungen statt nur dokumentiert.
- Dependabot würde ständig Updates für bewusst gepinnte Versionen vorschlagen. Updates testen wir gezielt.
- Die CI braucht keine Zugangsdaten, also auch keine GitHub Secrets.

**Offen:** Branch-Schutz für `main` (Merge nur per Pull Request mit grüner CI) muss der Repo-Inhaber in den GitHub-Einstellungen setzen. Bei privaten Repos setzt GitHub das nur mit einem Pro-Konto durch.

## 2026-11-01 – Lange Prompts nicht über den RunPod-HTTP-Proxy

**Entscheidung:** LiteLLM und die Benchmark-Skripte erreichen vLLM per SSH-Tunnel oder über einen direkt freigegebenen TCP-Port. Der HTTP-Proxy (`<pod-id>-8000.proxy.runpod.net`) dient höchstens für kurze Funktionstests.

**Warum:** Im B300-Test vom 01.10.2026 trennte der Proxy stille Verbindungen nach ca. 2 Minuten. Ein kalter 1M-Prompt braucht auf 2× RTX PRO 6000 bei GLM-5.3-Flash ca. 4,5–5 Minuten bis zum ersten Token, ein 500k-Prompt etwa 2 Minuten.

**Offen:** Ob der direkte TCP-Port auf dem gewählten RunPod-Host eine öffentliche IP bekommt – wird in Phase 4 geprüft.

**Quelle:** [Erfahrungen](erfahrungen.md)

## 2026-11-01 – Lokaler Stack als Docker Swarm statt Docker Compose

**Entscheidung:** LiteLLM und der Mock-Server laufen als Swarm-Stack (`docker stack deploy`) auf dem Mediaserver (Linux), zunächst auf einem einzigen Node. Die bestehende OpenWebUI dort (Port 8081, Compose) wird weiter genutzt und nur um LiteLLM als Verbindung ergänzt. Der PC mit WSL dient zum Entwickeln und Reviewen; die zweite OpenWebUI dort (Port 3000) bleibt unberührt.

**Warum:** Native Docker Secrets für Zugangsdaten, Healthchecks mit automatischem Neustart, und das Stack-File kann später auf weitere Nodes wachsen. Der Mediaserver läuft dauerhaft und hostet die OpenWebUI, die tatsächlich genutzt wird; aus WSL heraus wäre LiteLLM für andere Rechner wegen des WSL2-NAT nur mit Zusatzaufwand erreichbar.

**Folgen:**
- Swarm und die bestehenden Compose-Container laufen auf demselben Docker-Daemon nebeneinander. `docker swarm init` ändert an den Compose-Containern nichts.
- `docker stack deploy` liest keine `.env`-Datei automatisch. Zugangsdaten des Stacks kommen als Docker Secrets, die `.env` bleibt für die Skripte (RunPod, Hugging Face).
- Compose-Felder wie `build`, `container_name` und `depends_on` werden von Swarm ignoriert. Es werden nur fertige, gepinnte Images verwendet.
- Swarm umfasst nur den Mediaserver. Der RunPod-Pod kann kein Swarm-Node werden: kein Docker im Pod, und Swarm braucht UDP, das RunPod nicht unterstützt.

## 2026-10-31 – GLM-5.3-Flash über die Runtime von T.J. Purtell, Profil `k3`

**Entscheidung:** GLM-5.3-Flash wird mit `tpurtell/glm-5.3-flash-ext3-2x-rtx` getestet, nicht mit Karmic.

**Warum:**
- Einziges gefundenes Rezept mit nachgewiesenen 1M Tokens Kontext auf 2× RTX PRO 6000 (Nadeltest mit sechs Fakten bestanden).
- EXL3-Checkpoint mit ca. 127 GiB statt 166–175 GiB bei NVFP4 – dadurch 16 parallele Slots und ein KV-Pool von rund 2,8–2,9 Mio. Tokens.
- Komplett über Umgebungsvariablen steuerbar, passt zu RunPod.
- Profil `k3` statt Standard `k325`: bei 16 parallelen Anfragen deutlich mehr Durchsatz (laut Upstream 1.119 statt 832 tok/s), einzeln praktisch gleich.

**Bekannte Schwächen:** Prefill nur ca. 4.200–4.600 tok/s (128k ≈ 30 s bis zum ersten Token). DFlash2-Drafter nur für Forschung/Evaluation lizenziert.

**Quellen:** `tpurtell/glm-5.3-flash-ext3-2x-rtx`, `samuelcardillo/glm-5.3-flash-2x-rtx-pro-6000-blackwell`

## 2026-10-31 – P2P zwischen den Karten ist Pflicht

**Entscheidung:** Ein RunPod-Host, auf dem CUDA-P2P zwischen beiden Karten nicht funktioniert, wird nicht genutzt.

**Warum:** Karmic (PCIe-All-Reduce) und das Purtell-Rezept (prüft P2P vor dem Start) bauen darauf auf. Der verbreitete Workaround `NCCL_P2P_DISABLE=1` aus 2025 verhindert Hänger, kostet aber Leistung. BIOS/IOMMU lassen sich auf RunPod nicht ändern.

## 2026-10-30 – Karmic Kraken für DeepSeek V4 Flash

**Entscheidung:** DeepSeek V4 Flash läuft mit dem Karmic-Kraken-Image von Local Inference Lab, gepinnt per Digest.

**Warum:**
- Upstream-vLLM hat für die Sparse-Attention von DeepSeek V4 auf SM120 (RTX PRO 6000) keinen fertigen Kernel. Karmic bringt ihn mit (B12X), dazu PCIe-optimiertes All-Reduce, KV-Offloading und schnelles Laden (InstantTensor).
- Bekannte Referenz: Community-Rezepte für DeepSeek V4 Flash auf RTX PRO 6000 (u. a. das rtx6kpro-Wiki) setzen auf genau diese Image-Linie.

**Risiken:** Pre-Release, sehr hohes Release-Tempo, wenige Maintainer. Deshalb nie den `-beta`-Tag, immer Digest.

**Quelle:** `local-inference-lab/blackwell-llm-docker`

## 2026-10-30 – RunPod als Anbieter, LiteLLM und OpenWebUI lokal

**Entscheidung:** GPU-Instanzen bei RunPod, Gateway und Frontend auf dem eigenen Rechner.

**Warum:**
- Minutengenaue Abrechnung, Network Volumes für Gewichte und Caches, API für Automatisierung.
- In RunPod-Pods ist kein Docker und kein Docker Compose möglich – das vLLM-Image wird direkt das Pod-Image, alles andere läuft lokal.

**Offen:** Ob RunPod genug System-RAM und `/dev/shm` für KV-Offloading bereitstellt – wird in Phase 4 geprüft.

## 2026-10-30 – Eigenes privates Repo, strikt isoliert

**Entscheidung:** Neues privates Repo im persönlichen GitHub-Account. Kein Code, keine Configs und keine Zugangsdaten aus anderen Stack-Projekten.

**Warum:** Ein eigenständiges Repo ohne fremde Abhängigkeiten (Actions-Runner, MCPs, MCPOs) bleibt überschaubar und lässt sich jederzeit vollständig nachvollziehen.
