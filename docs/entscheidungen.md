# Entscheidungslog

Kurz festgehalten: was entschieden wurde, warum, und wo es herkommt. Neue Einträge oben.

---

## 2026-11-01 – Lange Prompts nicht über den RunPod-HTTP-Proxy

**Entscheidung:** LiteLLM und die Benchmark-Skripte erreichen vLLM per SSH-Tunnel oder über einen direkt freigegebenen TCP-Port. Der HTTP-Proxy (`<pod-id>-8000.proxy.runpod.net`) dient höchstens für kurze Funktionstests.

**Warum:** Im B300-Test vom 01.10.2026 trennte der Proxy stille Verbindungen nach ca. 2 Minuten. Ein kalter 1M-Prompt braucht auf 2× RTX PRO 6000 bei GLM-5.3-Flash ca. 4,5–5 Minuten bis zum ersten Token, ein 500k-Prompt etwa 2 Minuten.

**Offen:** Ob der direkte TCP-Port auf dem gewählten RunPod-Host eine öffentliche IP bekommt – wird in Phase 4 geprüft.

**Quelle:** [Erfahrungen](erfahrungen.md)

## 2026-11-01 – Lokaler Stack als Docker Swarm statt Docker Compose

**Entscheidung:** LiteLLM, OpenWebUI und der Mock-Server laufen lokal in WSL als Swarm-Stack (`docker stack deploy`), zunächst auf einem einzigen Node.

**Warum:** Native Docker Secrets für Zugangsdaten, Healthchecks mit automatischem Neustart, und das Stack-File kann später auf weitere Nodes wachsen.

**Folgen:**
- `docker stack deploy` liest keine `.env`-Datei automatisch. Zugangsdaten des Stacks kommen als Docker Secrets, die `.env` bleibt für die Skripte (RunPod, Hugging Face).
- Compose-Felder wie `build`, `container_name` und `depends_on` werden von Swarm ignoriert. Es werden nur fertige, gepinnte Images verwendet.
- Swarm umfasst nur die lokale Seite. Der RunPod-Pod kann kein Swarm-Node werden: kein Docker im Pod, und Swarm braucht UDP, das RunPod nicht unterstützt.

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
- Wird beruflich bereits für DeepSeek V4 Flash Vision genutzt – bekannte Referenz.

**Risiken:** Pre-Release, sehr hohes Release-Tempo, wenige Maintainer. Deshalb nie den `-beta`-Tag, immer Digest.

**Quelle:** `local-inference-lab/blackwell-llm-docker`

## 2026-10-30 – RunPod als Anbieter, LiteLLM und OpenWebUI lokal

**Entscheidung:** GPU-Instanzen bei RunPod, Gateway und Frontend auf dem eigenen Rechner.

**Warum:**
- Minutengenaue Abrechnung, Network Volumes für Gewichte und Caches, API für Automatisierung.
- In RunPod-Pods ist kein Docker und kein Docker Compose möglich – das vLLM-Image wird direkt das Pod-Image, alles andere läuft lokal.

**Offen:** Ob RunPod genug System-RAM und `/dev/shm` für KV-Offloading bereitstellt – wird in Phase 4 geprüft.

## 2026-10-30 – Eigenes privates Repo, getrennt vom Beruf

**Entscheidung:** Neues privates Repo im persönlichen GitHub-Account. Nichts aus dem beruflichen Stack wird übernommen.

**Warum:** Deployment aus dem beruflichen Repo ist untersagt, und der dortige Stack hat zu viele Abhängigkeiten (Actions-Runner, MCPs, MCPOs).
