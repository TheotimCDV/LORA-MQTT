import time
import random
import json
import paho.mqtt.publish as publish
from meshtastic.protobuf import mesh_pb2, mqtt_pb2, portnums_pb2, telemetry_pb2
from meshtastic.protobuf.mesh_pb2 import NeighborInfo, Neighbor


MQTT_BROKER = "192.168.20.57"
MESH_TOPIC = "msh/CO/cajica/{device}"
INFLUX_TOPIC = "msh/CO/cajica/{device}"
CHANNEL_ID = "longFast"

POSITIONS = {
    "capteur1": (4.946154, -74.014070, 258),
    "capteur2": (4.939301, -74.009780, 258),
    "capteur3": (4.940871, -74.011995, 258)
}

ALL_NODE_IDS = [
    0xA1A1A101,
    0xA1A1A102,
    0xA1A1A103
]

def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def send_envelope(packet, node_id, device_name):
    envelope = mqtt_pb2.ServiceEnvelope()
    envelope.channel_id = CHANNEL_ID
    envelope.packet.CopyFrom(packet)
    envelope.gateway_id = f"!{node_id:016x}"
    try:
        publish.single(
            topic=MESH_TOPIC.format(device=device_name),
            payload=envelope.SerializeToString(),
            hostname=MQTT_BROKER,
            port=1883
        )
        log(f"📡 Protobuf envoyé → {device_name}")
    except Exception as e:
        log(f"❌ Erreur MQTT MeshView : {e}")

def send_nodeinfo(node_id, name, device_name):
    user = mesh_pb2.User()
    user.id = f"!{node_id:016x}"
    user.long_name = name
    user.short_name = name[:3].upper()
    user.hw_model = 43
    user.macaddr = bytes([random.randint(0, 255) for _ in range(6)])

    packet = mesh_pb2.MeshPacket()
    setattr(packet, "from", node_id)
    packet.to = 0xffffffff
    packet.id = random.randint(0, 2**32 - 1)

    data = mesh_pb2.Data()
    data.portnum = portnums_pb2.PortNum.NODEINFO_APP
    data.payload = user.SerializeToString()
    data.want_response = False

    packet.decoded.CopyFrom(data)
    send_envelope(packet, node_id, device_name)
    log(f"✅ NODEINFO envoyé → {device_name} ({user.long_name})")

def send_position(node_id, device_name):
    lat, lon, alt = POSITIONS[device_name]
    position = mesh_pb2.Position()
    position.latitude_i = int(lat * 1e7)
    position.longitude_i = int(lon * 1e7)
    position.altitude = int(alt)
    position.time = int(time.time())

    packet = mesh_pb2.MeshPacket()
    setattr(packet, "from", node_id)
    packet.to = 0xffffffff
    packet.id = random.randint(0, 2**32 - 1)

    data = mesh_pb2.Data()
    data.portnum = portnums_pb2.PortNum.POSITION_APP
    data.payload = position.SerializeToString()
    data.want_response = False

    packet.decoded.CopyFrom(data)
    send_envelope(packet, node_id, device_name)
    log(f"🗺️ Position envoyée → {device_name} ({lat}, {lon})")

def send_telemetry(node_id, device_name):
    temperature = round(20 + random.uniform(-3, 3), 2)
    humidity = round(50 + random.uniform(-10, 10), 2)
    light = random.randint(100, 500)

    json_payload = json.dumps({
        "temperature": temperature,
        "humidity": humidity,
        "light": light
    })

    try:
        publish.single(
            topic=INFLUX_TOPIC.format(device=device_name),
            payload=json_payload,
            hostname=MQTT_BROKER,
            port=1883
        )
        log(f"📤 JSON Influx → {device_name} : Temp={temperature}°C, Hum={humidity}%, Light={light}lux")
    except Exception as e:
        log(f"❌ Erreur MQTT InfluxDB : {e}")

    telemetry = telemetry_pb2.Telemetry()
    telemetry.time = int(time.time())
    telemetry.device_metrics.battery_level = random.randint(80, 101)
    telemetry.device_metrics.voltage = round(random.uniform(3.7, 4.3), 3)
    telemetry.device_metrics.channel_utilization = round(random.uniform(1, 3), 3)
    telemetry.device_metrics.air_util_tx = round(random.uniform(0.5, 1.5), 6)
    telemetry.device_metrics.uptime_seconds = random.randint(50000, 300000)
    telemetry.environment_metrics.temperature = temperature
    telemetry.environment_metrics.relative_humidity = humidity

    packet = mesh_pb2.MeshPacket()
    setattr(packet, "from", node_id)
    packet.to = 0xffffffff
    packet.id = random.randint(0, 2**32 - 1)

    data = mesh_pb2.Data()
    data.portnum = portnums_pb2.PortNum.TELEMETRY_APP
    data.payload = telemetry.SerializeToString()
    data.want_response = False

    packet.decoded.CopyFrom(data)
    send_envelope(packet, node_id, device_name)
    log(f"📈 TELEMETRY envoyé → {device_name}")

def send_text_message(from_node_id, to_node_id, message_text, device_name):
    from google.protobuf.internal.encoder import _VarintBytes

    def encode_text_payload(msg_text):
        tag = (1 << 3) | 2  # field 1, wire type 2 (length-delimited)
        msg_bytes = msg_text.encode("utf-8")
        return bytes([tag]) + _VarintBytes(len(msg_bytes)) + msg_bytes

    packet = mesh_pb2.MeshPacket()
    setattr(packet, "from", from_node_id)
    packet.to = to_node_id
    packet.id = random.randint(0, 2**32 - 1)
    packet.channel = 8

    data = mesh_pb2.Data()
    data.portnum = portnums_pb2.PortNum.TEXT_MESSAGE_APP
    data.payload = encode_text_payload(message_text)
    data.want_response = False
    data.bitfield = 1

    packet.decoded.CopyFrom(data)

    envelope = mqtt_pb2.ServiceEnvelope()
    envelope.packet.CopyFrom(packet)
    envelope.channel_id = CHANNEL_ID
    envelope.gateway_id = f"!{from_node_id:016x}"

    try:
        publish.single(
            topic=MESH_TOPIC.format(device=device_name),
            payload=envelope.SerializeToString(),
            hostname=MQTT_BROKER,
            port=1883
        )
        log(f"💬 Message envoyé → {device_name} : \"{message_text}\"")
    except Exception as e:
        log(f"❌ Erreur MQTT message texte : {e}")

def send_neighbors(node_id, other_node_ids, device_name):
    neighbor_info = NeighborInfo()

    for other_id in other_node_ids:
        n = neighbor_info.neighbors.add()
        n.node_id = other_id
        n.snr = round(random.uniform(10, 30), 1)
        n.last_rx_time = int(time.time())
        n.node_broadcast_interval_secs = 360

    packet = mesh_pb2.MeshPacket()
    setattr(packet, "from", node_id)
    packet.to = 0xffffffff
    packet.id = random.randint(0, 2**32 - 1)

    data = mesh_pb2.Data()
    data.portnum = portnums_pb2.PortNum.NEIGHBORINFO_APP
    data.payload = neighbor_info.SerializeToString()
    data.want_response = False

    packet.decoded.CopyFrom(data)
    send_envelope(packet, node_id, device_name)
    log(f"📡 NEIGHBORS envoyé → {device_name} ({len(other_node_ids)} voisins)")


def run_device(node_id, name, device_name):
    log(f"🚀 Démarrage de {device_name}")
    other_nodes = [nid for nid in ALL_NODE_IDS if nid != node_id]
    send_nodeinfo(node_id, name, device_name)
    send_neighbors(node_id, other_nodes, device_name)

    time.sleep(0.5)
    send_position(node_id, device_name)
    time.sleep(0.5)
    send_telemetry(node_id, device_name)
    time.sleep(0.5)

    # ✅ Obtenir la liste des autres node_id réels
    other_nodes = [nid for nid in ALL_NODE_IDS if nid != node_id]

    messages = [
        "Salut !",
        "Capteur opérationnel.",
        "Mesures stables pour l’instant.",
        "Besoin de vérification météo ?",
        "C’est calme ici.",
        "Tu reçois bien ?"
    ]

    last_message_time = time.time()
    last_routing_time = time.time()

    while True:
        now = time.time()

        if now - last_message_time >= 20:
            to_node = random.choice(other_nodes)
            msg = random.choice(messages)
            send_text_message(node_id, to_node, msg, device_name)
            last_message_time = now
        else:
            choice = random.randint(0, 3)
            if choice == 0:
                send_nodeinfo(node_id, name, device_name)
            elif choice == 1:
                send_telemetry(node_id, device_name)
            elif choice == 2:
                send_position(node_id, device_name)

        time.sleep(random.randint(8, 12))

if __name__ == "__main__":
    import multiprocessing

    capteurs = [
        (0xA1A1A101, "Capteur Patio", "capteur1"),
        (0xA1A1A102, "Capteur Salle", "capteur2"),
        (0xA1A1A103, "Capteur Extérieur", "capteur3")
    ]

    jobs = []
    for nid, name, dev in capteurs:
        p = multiprocessing.Process(target=run_device, args=(nid, name, dev))
        p.start()
        jobs.append(p)
