# Mediaserver: Umzug von Snap-Docker auf docker-ce

Einmalige Anleitung für den Mediaserver (Ubuntu 24.04.5, Kernel 6.14). Ausführen von Hand, Schritt für Schritt. Bei jeder unerwarteten Ausgabe **stoppen** und die Ausgabe prüfen lassen.

## Warum

Der Snap-Docker läuft in einem AppArmor-Käfig (`snap.docker.dockerd`), der Netzwerkzugriffe des Daemons blockiert. Befund vom 03.11.2026:

- `docker pull` scheitert bei **jedem** Image, auch `hello-world`: `lookup … on 127.0.0.53:53: write: permission denied`
- Kernel-Log: `apparmor="DENIED" … profile="snap.docker.dockerd" comm="docker-proxy" … denied="receive"`, Zähler über 1,1 Mio.
- DNS auf dem Host funktioniert (`getent hosts ghcr.io`), die Ursache liegt also allein im Käfig.
- Gleiches Fehlerbild öffentlich bekannt: [canonical/docker-snap#350](https://github.com/canonical/docker-snap/issues/350), ohne Lösung

Folge: keine Image-Updates für OpenWebUI, Home Assistant, Plex & Co., und Phase 1 des Projekts ist blockiert.

`docker-ce` 29.9.0, das offizielle Paket von Docker, ist bereits installiert, aber inaktiv. Es läuft ohne Snap-Käfig.

**Abwägung:** Der Snap war damals bewusst gewählt, um die Terminal-Container zusätzlich einzusperren. Diese äußere Schicht fällt weg. Gezielte Härtung der Terminals (gVisor, eigenes Netz, Limits) ist als Folgeschritt vorgesehen, siehe unten.

## Ausgangslage

| | |
|---|---|
| Laufender Daemon | Snap-Docker 29.8.0, Revision 3618 |
| Datenordner | `/var/snap/docker/common/var-lib-docker` (24 GB) |
| Freier Platz auf `/` | 362 GB, Umzug auf dieselbe Platte |
| Einstellung im Snap | nur `"log-level": "error"` |
| Compose-Ordner | `~/docker/localAI`, `~/docker/mediaserver` |

**Daten der Container:**

| Art | Container | Beim Umzug |
|---|---|---|
| Ordner unter `/home/kalavera/docker/…` (bind) | openwebui, nginx-landing, lldap, homeassistant, plex, ollama | bleiben unverändert liegen |
| externe Platte (bind) | plex: `/home/kalavera/externe_platte` | bleibt unverändert |
| Docker-Volumes | open-terminal, terminal-tristan/-leo/-julia/-cath, wochenplaner | werden mitkopiert, Original bleibt |
| Images | alle, auch das selbst gebaute `localai-wochenplaner` | werden mitkopiert |

## Schritt 0 – Vorprüfung (noch kein Ausfall)

```bash
command -v docker                                  # erwartet: /usr/bin/docker
docker compose version                             # muss eine Version zeigen
sudo ls -A /var/lib/docker 2>/dev/null | head      # sollte leer sein oder fehlen
cat /etc/docker/daemon.json 2>/dev/null            # gibt es schon eine Datei?
```

Weiter nur, wenn `docker compose version` funktioniert und `/var/lib/docker` leer ist oder fehlt.

## Schritt 1 – Snap-Docker stoppen

Ab hier sind alle Container aus.

```bash
sudo snap stop --disable docker
pgrep -a dockerd || echo "kein dockerd mehr aktiv"
```

## Schritt 2 – Daten kopieren

Das Original bleibt unverändert und ist der Rückweg.

```bash
sudo rsync -aHAX --numeric-ids --info=progress2 \
  /var/snap/docker/common/var-lib-docker/ /var/lib/docker/
```

`-aHAX` übernimmt Rechte, Hardlinks, ACLs und erweiterte Attribute, die das Speicherformat von Docker (overlay2) braucht.

## Schritt 3 – Einstellung übernehmen

```bash
echo '{ "log-level": "error" }' | sudo tee /etc/docker/daemon.json
```

## Schritt 4 – docker-ce starten

```bash
sudo systemctl enable --now docker.socket docker.service
docker info --format '{{.DockerRootDir}}  {{.ServerVersion}}  Swarm: {{.Swarm.LocalNodeState}}'
# erwartet: /var/lib/docker  29.9.0  Swarm: active
```

## Schritt 5 – Container starten und prüfen

```bash
cd ~/docker/localAI && docker compose up -d
cd ~/docker/mediaserver && docker compose up -d
docker ps --format '{{.Names}}  {{.Status}}'

docker pull hello-world                                                   # DNS-Test, scheiterte vorher
sudo journalctl -k --since "10 min ago" | grep -c 'apparmor="DENIED"'    # erwartet: 0
```

Von Hand prüfen: OpenWebUI-Login (Port 8081), ein Terminal, Home Assistant, Plex.

## Rückweg

Falls in Schritt 4 oder 5 etwas nicht stimmt. Danach ist alles wie vorher, die Snap-Daten sind unberührt.

```bash
sudo systemctl disable --now docker.service docker.socket
sudo snap start --enable docker
```

## Schritt 6 – Aufräumen (frühestens nach einer Woche stabilem Betrieb)

```bash
sudo snap remove --purge docker    # löscht den Snap samt der alten 24-GB-Kopie
```

## Danach

1. **Projekt weiter:** `cd ~/projekte/SwarmLLM_Benchmark/local && ./pin-images.sh`
2. **Terminals härten** (eigener Schritt): gVisor (`runtime: runsc`) für die Terminal-Container, eigenes Netz ohne Zugriff auf Home Assistant und lldap, `no-new-privileges`, Limits für Prozesse und Speicher.
3. **Ollama auf die GPU** (optional, eigener Schritt): Ollama rechnet derzeit auf der CPU (keine GPU-Anforderung, kein NVIDIA-Toolkit). Falls die RTX 4070 in diesem Rechner steckt: NVIDIA Container Toolkit installieren, `gpus: all` in der Compose-Datei.
