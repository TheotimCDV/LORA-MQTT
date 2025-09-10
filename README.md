# UMNG Smart Campus — LoRa MQTT Stack with MeshView

This repository provides a containerized IoT stack for real-time monitoring and visualization of LoRa/MQTT sensor data. The centerpiece is **MeshView**, which displays a live map of Meshtastic nodes alongside complementary services: Mosquitto, Node-RED, InfluxDB, and Grafana.

---

## Architecture

```mermaid
flowchart LR
  subgraph Device
    MCU[LoRa Sensor / Meshtastic Node]
  end

  MCU -- uplink --> GW((LoRa Gateway / MQTT Publisher))

  subgraph Docker Host
    MOSQ[(Mosquitto MQTT Broker)]
    NR[Node-RED]
    IFX[(InfluxDB 2.x)]
    GRA[Grafana]
    MV[MeshView Web App]
  end

  GW -->|MQTT topics| MOSQ
  MOSQ -->|subscribe| MV
  MOSQ -->|subscribe| NR
  NR -->|write| IFX
  IFX -->|visualize| GRA
```

---

## Components

- **Mosquitto** → lightweight MQTT broker for sensor message routing.  
- **Node-RED** → low-code environment for message parsing and routing to InfluxDB.  
- **InfluxDB** → time-series database for sensor metrics.  
- **Grafana** → dashboards for visualization of stored metrics.  
- **MeshView** → Python web app (default port `8081`) that subscribes to MQTT topics and displays nodes, conversations, graphs, and maps.

---

## MeshView — what it is

**MeshView** is a Python app that:
- Subscribes to one or more MQTT topics (e.g. Meshtastic frames).
- Parses packets and stores them in a database (SQLite by default).
- Serves a web UI (default **port 8081**) with sections like *Nodes*, *Conversations*, *Graphs*, *Stats*, *Net*, *Map*, *Top*.
- Supports optional TLS for the web server and site branding (title, message, domain).

In this stack, the `Dockerfile` does:
```dockerfile
FROM python:3.12-slim
# ...
RUN git clone --recurse-submodules https://github.com/pablorevilla-meshtastic/meshview.git .
# ...
CMD ["/app/env/bin/python3", "mvrun.py", "--config", "config.ini"]
```
So MeshView runs with the **local** `config.ini` you edit below.

---

## **Configure MeshView** (`config.ini`)

This file has four sections: `[server]`, `[site]`, `[mqtt]`, `[database]`. The defaults found here are tailored for your sample deployment; adjust to your environment.

### 1) `[server]` — web server
Key | What it does | Recommended value
---|---|---
`bind` | Bind address | `"*"` (all interfaces) or `"0.0.0.0"`
`port` | HTTP port MeshView listens on | `8081` (mapped as `8081:8081` in compose)
`tls_cert` | Path to PEM certificate (enables HTTPS) | leave empty for HTTP
`acme_challenge` | Optional ACME challenge directory | leave empty unless terminating TLS here

> If you terminate TLS at a reverse proxy (recommended), keep `tls_cert` empty and expose MeshView over HTTP internally.

### 2) `[site]` — branding & feature flags
Key | What it does | Example
---|---|---
`domain` | Public FQDN (for links/branding) | `mesh.local` or leave empty
`title` | Page title | `"Réseau Mesh UMNG"`
`message` | Banner text on homepage | Short description of your network
`nodes`/`conversations`/`everything`/`graphs`/`stats`/`net`/`map`/`top` | Enable/disable UI sections | `True`/`False`
`map_top_left_lat` / `map_top_left_lon` | Map viewport (NW corner) | Decimal degrees
`map_bottom_right_lat` / `map_bottom_right_lon` | Map viewport (SE corner) | Decimal degrees
`weekly_net_message` | Optional weekly net check‑in note | Free text
`net_tag` | Hashtag used to tag net messages | e.g. `#UMNGMeshNet`

> **Tip:** Leave all sections `True` to start; tighten later if needed.

### 3) `[mqtt]` — **must be correct**
Key | What it does | Required
---|---|---
`server` | **Hostname/IP** of your MQTT broker | **Yes** — in Docker, use the **service name**: `mosquitto` (or your host/IP)
`port` | Broker port | Usually `1883` (or `8883` for TLS)
`username` / `password` | Credentials if your broker requires auth | Optional
`topics` | JSON array of topic filters MeshView subscribes to | **Yes** (e.g. `["msh/CO/cajica/#"]`)

> In this project the default is `server = mosquitto` and `topics = ["msh/CO/cajica/#"]`. If running everything via `docker-compose` on one network, set `server = mosquitto` so MeshView resolves the broker by service name.

### 4) `[database]` — storage backend
Key | What it does | Default
---|---|---
`connection_string` | SQLAlchemy URL for async DB | `sqlite+aiosqlite:///packets.db`

- Keep SQLite for simple setups (data persisted in the container volume if you mount one).
- For Postgres: `postgresql+asyncpg://user:pass@host:5432/dbname`




---

## Node-RED flows (how they relate)

- **MQTT input**: subscribes to `msh/CO/cajica/#` (see `nodered/flows.json`).  
  The broker node currently points to a LAN IP (`192.168.31.154`). **Change it to `mosquitto`** (service name) or your broker’s host.

- **Parsing**: a Function node converts incoming JSON (e.g. `{temperature, humidity, luminosity_percent, solar_irradiance, solar_class, device}`) into a measurement:
  ```js
  msg.payload = [ { temperature, humidity, luminosity_percent, solar_irradiance, solar_class }, { device } ];
  msg.measurement = "capteurs";
  ```

- **InfluxDB write**: uses an InfluxDB 2.x config node with `org = "MyOrg"` and `bucket = "LORA"` to persist metrics for Grafana dashboards.

## InfluxDB & Grafana Accounts

### InfluxDB (2.x)
- Current default credentials (from `.env` file):
  - **Username**: `admin`
  - **Password**: `admin123`
  - **Organization**: `MyOrg`
  - **Bucket**: `LORA`

- On **first startup with an empty volume**, InfluxDB is bootstrapped using the environment variables defined in `.env` (referenced in `docker-compose.yml`):
  - `INFLUX_USER`
  - `INFLUX_PASSWORD`
  - `INFLUX_ORG`
  - `INFLUX_BUCKET`
  - *(optional)* `INFLUX_TOKEN`

- ⚠️ These variables are **only applied once**. If the `./influxdb` folder already contains data, changing them will not update the existing account.

- To apply new credentials:
  1. Stop the stack:  
     ```bash
     docker compose down
     ```
  2. Remove the InfluxDB volume or folder (⚠️ data loss):  
     ```bash
     rm -rf ./influxdb/*
     ```
  3. Relaunch:  
     ```bash
     docker compose up -d
     ```

- If you don’t want to wipe data, you can change the password manually from inside the container:  
  ```bash
  docker compose exec influxdb influx user password --name admin

Node-RED writes sensor data into the bucket `LORA` under measurement `capteurs` with fields:
- `temperature` (°C)
- `humidity` (%)
- `luminosity_percent` (%)
- `solar_irradiance` (no unit)
- `solar_class` (categorical)

Each data point is tagged with the `device` identifier.

---
## Grafana

**URL:** http://localhost:3000  
**Admin credentials (from `.env`):**
- **Username:** `admin`
- **Password:** `admin123`

> These credentials are read from `.env` via `GRAFANA_USER` and `GRAFANA_PASSWORD` and are applied **only on first startup** when the `./grafana` volume is empty.

### What persists
Grafana stores its database in `./grafana` (mapped to `/var/lib/grafana`).  
If this folder already contains `grafana.db`, changing the env variables will **not** change the admin credentials.

### Resetting / changing the admin password
- Prefer the web UI: **Configuration → Users** (top-left gear icon).
- Or via CLI inside the container:
  ```bash
  docker compose exec grafana grafana-cli admin reset-admin-password <NEW_PASSWORD>

#### What already exists
A dashboard is already created with panels for:
- Current temperature and temperature over the last 24 hours  
- Current humidity and humidity over the last 24 hours  
- Current solar irradiance and irradiance over the last 24 hours  
- Solar class (categorical)

These panels are configured but will show *No data* until the datasource is correctly connected to InfluxDB and Node-RED starts writing values.

#### What needs to be done
1. In Grafana, go to **Configuration → Data sources → Add data source**.  
2. Select **InfluxDB** and configure:
   - **URL:** `http://influxdb:8086`
   - **Query language:** Flux
   - **Organization:** `MyOrg`
   - **Bucket:** `LORA`
   - **Token:** generate one in the InfluxDB UI if none is set in `.env`
3. Save & test the datasource.  
4. Edit the dashboard panels if needed and make sure queries reference:
   - Measurement = `capteurs`
   - Fields = `temperature`, `humidity`, `solar_irradiance`, `solar_class`
   - Tag = `device` (add a variable in the dashboard to filter by device).

#### Recommended setup
- **Temperature:** last value (5m) + average over 24h, thresholds green < 25 °C, orange 25–30 °C, red > 30 °C  
- **Humidity:** last value + average over 24h, thresholds green 40–60 %  
- **Solar irradiance / Solar class:** display last values without thresholds  
- **Device filter:** add a dashboard variable `device` from InfluxDB tags to filter panels per device

---

### Troubleshooting
- If all panels show **No data**:
  - Ensure Node-RED is writing to InfluxDB (`bucket=LORA`, `org=MyOrg`).
  - Verify Grafana datasource points to `http://influxdb:8086` with Flux, correct org, bucket, and token.
  - Adjust the time range (e.g. “Last 24h” instead of “Last 5m”).
  - Check container logs if data still doesn’t appear.
  
## Installation & Usage

```bash
# Build MeshView (Dockerfile in repo)
docker compose build

# Start all services
docker compose up -d

# Access services
MeshView:   http://localhost:8081
Node-RED:   http://localhost:1880
Grafana:    http://localhost:3000
InfluxDB:   http://localhost:8086
Mosquitto:  tcp://localhost:1883
```
