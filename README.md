# LORA-MQTT


Sur nodered, changer l'host mqtt en fonction de l'adresse IP de l'hôte sinon pas d'envoie via le broker

Pour connecter les capteurs avec meshview :


### 🪜 Étapes

#### 1. **Configurer le broker MQTT**

Dans `config.ini` de Meshview (section `[mqtt]`), ajoute ton topic personnalisé :

```ini
topics = ["msh/CO/cajica/#"]
server = ton.ip.local.serveur  # Exemple: 192.168.1.100
port = 1883
username = ton_user
password = ton_mdp
```

---

#### 2. **Choisir un topic pour ton capteur**

Par convention Meshview, les topics ont cette structure :

```
msh/<pays>/<ville>/<identifiant_du_capteur>
```

**Exemple** : `msh/CO/cajica/meteo01`

---

#### 3. **Adapter le code de ton capteur**

Voici un exemple complet en MicroPython à adapter sur ton microcontrôleur :

```python
mqtt_host = "192.168.1.100"  # IP de ton serveur MQTT
mqtt_port = 1883
mqtt_topic = "msh/CO/cajica/meteo01"

payload = {
    "id": "meteo01",
    "from": "meteo01",
    "to": "ffffffff",
    "rx_time": int(time.time()),
    "rx_rssi": -60,
    "rx_snr": 7.5,
    "decoded": {
        "payload": {
            "temperature": temp,     # float
            "humidity": hum          # float
        }
    },
    "position": {
        "latitude": 5.0261,
        "longitude": -74.0299,
        "altitude": 2550
    }
}

mqtt_client.publish(mqtt_topic, ujson.dumps(payload))
```

✔️ **Important** : les champs `position`, `rx_time`, `from` et `decoded` sont **nécessaires pour que Meshview comprenne la trame**.

---

#### 4. **Vérifier la réception des données**

* Dans l'interface **Meshview** sur `http://localhost:8081` :

  * Une nouvelle **node** doit apparaître automatiquement.
  * Clique sur la node pour voir les données reçues (température, humidité...).

---

#### 5. **(Optionnel) Intégration avec InfluxDB / Grafana**

Si tu utilises Node-RED pour router les messages vers InfluxDB :

* Abonne-toi au topic `msh/CO/cajica/#` dans Node-RED.
* Pars les messages MQTT et extrais les champs utiles.
* Envoie les données dans InfluxDB → Visualise-les dans Grafana.

---

### 🧪 Exemple de test en local

Tu peux tester manuellement avec :

```bash
mosquitto_pub -h localhost -t msh/CO/cajica/meteo01 -m '{"id":"meteo01","from":"meteo01","rx_time":1720000000,"rx_rssi":-60,"rx_snr":7.5,"decoded":{"payload":{"temperature":23.5,"humidity":40}},"position":{"latitude":5.0261,"longitude":-74.0299,"altitude":2550}}'
```




Exemple de config.ini pour plusieurs capteurs,

# -------------------------
# Server Configuration
# -------------------------
[server]
bind = *
port = 8081
tls_cert =
acme_challenge =

# -------------------------
# Site Appearance & Behavior
# -------------------------
[site]
domain =
title = UMNG Sensor Network
message = Capteurs déployés autour du campus UMNG à Cajicá, Colombie.
nodes = True
conversations = False
everything = True
graphs = True
stats = True
net = False
map = True
top = True

# Centrage carte autour du campus UMNG Cajicá
map_top_left_lat = 5.02
map_top_left_lon = -74.04
map_bottom_right_lat = 4.98
map_bottom_right_lon = -73.99

# -------------------------
# MQTT Broker Configuration
# -------------------------
[mqtt]
# Adresse de ton broker local en Docker
server = mosquitto
port = 1883
username =
password =
# Topics : un par dispositif
topics = ["msh/CO/cajica/pico1", "msh/CO/cajica/pico2"]

# -------------------------
# Database Configuration
# -------------------------
[database]
connection_string = sqlite+aiosqlite:///packets.db



Les capteurs (code micropython) doivent envoyés deux messages différents au broker MQTT, un servant à la collecte de données pour influxdb et les dashboards et un pour Meshview car ils attendent des formats de messages différents
Exemple meshview :
client.publish("msh/CO/cajica/pico1", '{"from": "pico1", "lat": 4.918, "lon": -74.027, "temperature": 24.5, "humidity": 48.0, "light": 310, "batteryLevel": 4.1, "snr": 7.2, "time": "2025-07-12T15:48:38Z"}')
