# Vključitev potrebnih knjižnic
import paho.mqtt.client as mqtt

# IP naslov MQTT Broker-ja (Mosquitto MQTT)
broker = "127.0.0.1"

# Port MQTT Broker-ja (Mosquitto MQTT)
port = 1883

# Ime topica - vrste
topic = "/data"

def on_connect(client, userdata, flags, reasonCode, properties=None):
  print("Povezava z MQTT: " + str(reasonCode))

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
  print("Prijava na topic")

def on_message(client, userdata, msg):
  print("Prejeto:" + msg.payload.decode())

# Nastavitev MQTT klienta
# clean_session: indicate if persistent connection is required
client = mqtt.Client(client_id="client_1", clean_session=False, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

# Povezava na MQTT broker
client.connect(broker, port, 60)

# Prijava na topic
# QOS 1: delivery at least once
client.subscribe(topic, qos=1)

# Callback funkcije
client.on_connect = on_connect     # Ob vzpostavitvi povezave na MQTT broker
client.on_subscribe = on_subscribe # Ob prijavi na topic
client.on_message = on_message     # Ob prejemu sporočila iz MQTT brokerja

# Neskončna zanka
client.loop_forever()