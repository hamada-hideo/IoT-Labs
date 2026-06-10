import paho.mqtt.client as mqtt
import time
import json
import threading
import os

import SenMLUtils as SenML

DIR = os.path.dirname(os.path.abspath(__file__))

class MQTTActuatorsControlBridge:
    def __init__(self, service):
        self.service = service
        self.catalog = service.cc
        
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            client_id=f"EventLog_Group12_{int(time.time())}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.sub_topic = data["mqtt"]["sub_topic"]
        self.pub_topic = data["mqtt"]["pub_topic"]

        self.broker_valid = threading.Event()
        threading.Thread(target=self._get_broker_connect_loop, daemon=True).start()

    def _get_broker_connect_loop(self):
        while True:
            time.sleep(self.catalog.loop_time)
            broker = self.catalog.get_broker()
            if broker:
                self.broker_host = broker["ip"]
                self.broker_port = broker["port"]
                try:
                    self.client.connect(self.broker_host, self.broker_port)
                except:
                    print(f"[MQTT Actuators Control] Impossibile connettersi al broker su {self.broker_host}:{self.broker_port}")
                self.broker_valid.set()
                break
    
    def _get_room_id_sensor_id(self, topic):
        segments = topic.split("/")
        return segments[4], segments[5]

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[MQTT Actuators Control] Connesso con successo al Broker su {self.broker_host}:{self.broker_port}!")
            self.client.subscribe([(self.sub_topic.format(room = room, id = id), 2) for room in self.service.state for id in self.service.state[room]])
            print(f"[MQTT Actuators Control] Subscribed to {[self.sub_topic.format(room = room, id = id) for room in self.service.state for id in self.service.state[room]]}")
        else:
            print(f"[MQTT Actuators Control] Errore di connessione. Codice: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            room, id = self._get_room_id_sensor_id(msg.topic)
            self.service._process_SenML(payload, room, id)
            self.client.publish(
                self.pub_topic.format(room = room, id = id), 
                json.dumps({
                    "message": "Command received"
                })
            )
        except json.JSONDecodeError:
            print(f"[MQTT Actuators Control - ERROR] Il payload da {msg.topic} non è un JSON valido.")
        except Exception as e:
            print(f"[MQTT Actuators Control - ERROR] Eccezione durante l'elaborazione del messaggio: {e}")

    def run(self):
        self.broker_valid.wait()
        self.running = True
        self.client.loop_start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
            self.running = False
            self.client.unsubscribe([self.sub_topic.format(room = room, id = id) for room in self.service.state for id in self.service.state[room]])
            self.client.loop_stop()
            self.client.disconnect()
            print("Disconnected")