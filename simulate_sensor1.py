import time
import random
import json
import paho.mqtt.publish as publish
from meshtastic.protobuf import mesh_pb2, mqtt_pb2, portnums_pb2, telemetry_pb2

MQTT_BROKER = "localhost"
MESH_TOPIC = "msh/CO/cajica/{device}"
INFLUX_TOPIC = "msh/CO/cajica/{device}"  # Même topic mais payload JSON

def send_envelope(packet, node_id, device_name):
    envelope = mqtt_pb2.ServiceEnvelope()
    envelope.channel_id = ""
    envelope.packet.CopyFrom(packet)
    envelope.gateway_id = f"!{node_id:016x}"
    publish.single(
        topic=MESH_TOPIC.format(device=device_name),
        payload=envelope.SerializeToString(),
        hostname=MQTT_BROKER,
        port=1883
    )

def send_user(node_id, name, device_name):
    user = mesh_pb2.User()
    user.id = f"!{node_id:016x}"
    user.long_name = name
    user.short_name = name[:3].upper()

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

def send_telemetry(node_id, device_name):
    # Valeurs simulées
    temperature = round(20 + random.uniform(-3, 3), 2)
    humidity = round(50 + random.uniform(-10, 10), 2)
    light = random.randint(100, 500)

    # ➤ MQTT JSON (InfluxDB)
    json_payload = json.dumps({
        "temperature": temperature,
        "humidity": humidity,
        "light": light
    })
    publish.single(
        topic=INFLUX_TOPIC.format(device=device_name),
        payload=json_payload,
        hostname=MQTT_BROKER,
        port=1883
    )

    # ➤ MQTT Protobuf (Meshview)
    telemetry = telemetry_pb2.Telemetry()
    telemetry.device_metrics.battery_level = random.randint(70, 95)
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

# -------------------
# MAIN Simulation
# -------------------
def run_device(node_id, name, device_name):
    send_user(node_id, name, device_name)
    time.sleep(0.5)
    while True:
        send_telemetry(node_id, device_name)
        time.sleep(10)

# Pour lancer les deux capteurs
if __name__ == "__main__":
    import multiprocessing
    capteurs = [
        (1, "Capteur Patio", "capteur1"),
        (2, "Capteur Salle", "capteur2")
    ]
    jobs = []
    for nid, name, dev in capteurs:
        p = multiprocessing.Process(target=run_device, args=(nid, name, dev))
        p.start()
        jobs.append(p)
