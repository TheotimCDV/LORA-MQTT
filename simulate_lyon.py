import time
import random
import paho.mqtt.publish as publish
from meshtastic.protobuf import mesh_pb2, mqtt_pb2, portnums_pb2, telemetry_pb2

TOPIC = "msh/US/capteur_lyon"

def send_envelope(packet, node_id):
    envelope = mqtt_pb2.ServiceEnvelope()
    envelope.channel_id = ""
    envelope.packet.CopyFrom(packet)
    envelope.gateway_id = f"!{node_id:016x}"
    publish.single(
        topic=TOPIC,
        payload=envelope.SerializeToString(),
        hostname="localhost",
        port=1883
    )

def send_user(node_id, name):
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
    send_envelope(packet, node_id)

def send_position(node_id, lat, lon, alt):
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
    send_envelope(packet, node_id)

def send_telemetry(node_id):
    telemetry = telemetry_pb2.Telemetry()
    telemetry.device_metrics.battery_level = random.randint(60, 95)
    telemetry.environment_metrics.temperature = round(25 + random.uniform(-2, 2), 2)
    telemetry.environment_metrics.relative_humidity = round(48 + random.uniform(-5, 5), 2)
    packet = mesh_pb2.MeshPacket()
    setattr(packet, "from", node_id)
    packet.to = 0xffffffff
    packet.id = random.randint(0, 2**32 - 1)
    data = mesh_pb2.Data()
    data.portnum = portnums_pb2.PortNum.TELEMETRY_APP
    data.payload = telemetry.SerializeToString()
    data.want_response = False
    packet.decoded.CopyFrom(data)
    print(f"[INFO] ➤ Temp: {telemetry.environment_metrics.temperature}°C | Humidité: {telemetry.environment_metrics.relative_humidity}%")
    send_envelope(packet, node_id)

# ---------- Simulateur Lyon ----------
if __name__ == "__main__":
    node_id = 0x22222222
    name = "Capteur_Lyon"
    lat = 45.75
    lon = 4.85
    alt = 180
    send_user(node_id, name)
    time.sleep(0.5)
    send_position(node_id, lat, lon, alt)
    time.sleep(0.5)
    while True:
        send_telemetry(node_id)
        time.sleep(10)
