# RunPod-Pod: getestete Einstellungen

Genau diese Einstellungen liefen am 01.10.2026 erfolgreich. Nur sie stehen hier. Andere Varianten (mehr Karten,
andere Modelle) sind **nicht getestet** und stehen gesondert in [`../docs/modellwahl.md`](../docs/modellwahl.md).

Wie man die Felder in der RunPod-Oberfläche ausfüllt, steht Schritt für Schritt in
[`../INSTALLATION.md`](../INSTALLATION.md).

## Welcher Pod

So wurde der Pod angelegt (Pods → **Deploy**) und lief:

| | Wert |
|---|---|
| GPU | **1× NVIDIA B300** (288 GB) |
| Ausstattung laut RunPod | 32 vCPU (Intel Xeon 6767P), 251 GB RAM |
| Preis laut RunPod | **7,96 $/h** (Secure oder Community Cloud ist nicht festgehalten) |
| Abrechnung | sekundengenau; On-Demand oder Spot ist nicht festgehalten |
| Ausgangs-Vorlage beim Deploy | **RunPod PyTorch** (Image `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`) |
| danach | per **Edit Pod** auf die Werte unten umgestellt |

Die PyTorch-Vorlage taugt nur als Ausgangspunkt: vLLM von Hand darin zu installieren scheiterte. Erst mit dem
vLLM-Image (unten) lief es.

## Pod-Einstellungen (Edit Pod)

| Feld | Wert |
|---|---|
| Container image | `vllm/vllm-openai:nightly` |
| Container start command | siehe unten |
| Container disk | `500` GB (belegt wurden 191 GB für die Modelldateien) |
| Expose HTTP ports | `8000` (bei uns `8888,8000`, 8888 stammte aus der Vorlage und wird nicht gebraucht) |
| Expose TCP ports | `22` (aus der Vorlage, für vLLM nicht nötig) |

## Container start command

Eine Zeile, ohne Leerzeichen am Anfang. Es sind **nur die Argumente**, denn der Einstiegspunkt des Images ist
bereits `vllm serve`.

```
nvidia/GLM-5.3-Flash-NVFP4 --served-model-name glm-5.3-flash --host 0.0.0.0 --port 8000 --tensor-parallel-size 1 --kv-cache-dtype fp8 --max-model-len 1048576 --max-num-seqs 4 --gpu-memory-utilization 0.92 --enable-auto-tool-choice --tool-call-parser glm47 --reasoning-parser glm47
```

| Argument | Wozu |
|---|---|
| `nvidia/GLM-5.3-Flash-NVFP4` | Modell von Hugging Face, 4-Bit (NVFP4), passt auf eine B300 |
| `--served-model-name glm-5.3-flash` | Name, unter dem das Modell in der API und in OpenWebUI erscheint |
| `--host 0.0.0.0 --port 8000` | lauscht auf Port 8000, der in RunPod freigegeben ist |
| `--tensor-parallel-size 1` | eine GPU |
| `--kv-cache-dtype fp8` | Kontextspeicher in FP8, halbiert den Platzbedarf |
| `--max-model-len 1048576` | 1 Mio. Token Kontext |
| `--max-num-seqs 4` | höchstens 4 Anfragen gleichzeitig, weitere warten (siehe Hinweis unten) |
| `--gpu-memory-utilization 0.92` | 92 % des Grafikspeichers für vLLM |
| `--enable-auto-tool-choice --tool-call-parser glm47` | Tool-Calls (Function Calling), nötig für Agenten und Terminal in OpenWebUI |
| `--reasoning-parser glm47` | trennt den Denkprozess von der Antwort |

**Hinweis zu `--max-num-seqs 4`:** Damit lag der Gesamtdurchsatz bei ~425 tok/s. Ab dem 5. gleichzeitigen Nutzer
warten Anfragen, und wer länger als ~2 Min. wartet, wird vom RunPod-Proxy getrennt. Ein höherer Wert (z. B. 16) ist
naheliegend, aber **nicht getestet**.

## Umgebungsvariablen

| Key | Value | Wozu |
|---|---|---|
| `VLLM_API_KEY` | Inhalt von `api-key.txt` | Schützt die API. Ohne ihn ist der Endpunkt offen im Internet |
| `VLLM_ENGINE_READY_TIMEOUT_S` | `3600` | vLLM wartet bis zu 1 h auf Laden + Kompilieren, statt vorher abzubrechen |
| `HF_HUB_ENABLE_HF_TRANSFER` | `1` | War gesetzt. vLLM meldet, dass die Variable veraltet ist. Sie schadet nicht und kann auch weg |

`PUBLIC_KEY` und `JUPYTER_PASSWORD` standen bei uns zusätzlich drin. Sie kamen aus der RunPod-Vorlage, mit der der
Pod angelegt wurde, und spielen für vLLM keine Rolle.

## Was nach dem Start passiert (gemessen)

| Phase | Dauer | Erkennbar an |
|---|---|---|
| Image laden | einige Minuten | Connect: „Downloading your container…“ mit Fortschrittsbalken |
| Modelldateien laden (191 GB) | ~5–10 Min. | im Log nichts! `du -sh /root/.cache/huggingface` im Web-Terminal wächst |
| Gewichte auf die GPU | ~1 Min. | `nvidia-smi`: ~183 GB belegt |
| Kontextspeicher anlegen | Sekunden | Log: `GPU KV cache size: 9,352,372 tokens` |
| Kernel kompilieren + Autotuning | ~6 Min. | Log: `JIT kernel warmup finished in 145.23s`, dann `[AutoTuner]` |
| bereit | | Log: `Application startup complete.`, Connect: Port 8000 „Ready“ |

Gesamt: rund 15 Minuten ab Start bis zur ersten Antwort.
