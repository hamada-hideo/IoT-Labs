# EXERCISE: Exercise 06 / Exercise 09 Extension - Actuator MQTT Bridge
# ACTOR: MQTTActuatorsControlBridge (Asynchronous Actuator Command Bridge)
# DESCRIPTION: Manages the MQTT messaging wrapper for the Actuator Control Server.
#              It dynamically resolves broker parameters, subscribes to control
#              topics for all configured rooms/devices, processes incoming SenML
#              commands, and issues execution feedback packets back to the broker.

# SECTION 1: SYSTEM ENVIRONMENT & PROTOCOL DEPENDENCIES
import paho.mqtt.client as mqtt
import time
import json
import threading
import os

import SenMLUtils as SenML

DIR = os.path.dirname(os.path.abspath(__file__))
# SECTION 2: CLASS INITIALIZATION & EVENT CALLBACK REGISTERING
class MQTTActuatorsControlBridge:
    def __init__(self, service):
        """
        Constructor method. Links the bridge with the main Actuator server instance,
        configures communication topics from assets, and prepares connection threads.
        """
        self.service = service
        self.catalog = service.cc
        
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            client_id=f"EventLog_Group12_{int(time.time())}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.config_file = os.path.join(DIR, "config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.sub_topic = data["mqtt"]["sub_topic"]
        self.pub_topic = data["mqtt"]["pub_topic"]

        self.broker_valid = threading.Event()
        threading.Thread(target=self._get_broker_connect_loop, daemon=True).start()
    # SECTION 3: AUTOMATED BROKER RESOLUTION & UTILITY PARSERS
    def _get_broker_connect_loop(self):
        """
        Asynchronous block routine. Periodically polls the central Catalog registry via REST 
        to extract active broker coordinates before establishing network connections.
        """
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
        """
        Deconstructs inbound raw MQTT topic string levels to dynamically map target 
        spatial environments (room) and resource hardware component indices (id).
        """
        segments = topic.split("/")
        return segments[4], segments[5]

    # SECTION 4: ASYNCHRONOUS PACKET INTERCEPT & ROUTING HOOKS
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """
        Asynchronous hook triggered upon connection response. Dynamically formats and
        subscribes to control topics for every device found online inside server memory.
        """
        if reason_code == 0:
            print(f"[MQTT Actuators Control] Connesso con successo al Broker su {self.broker_host}:{self.broker_port}!")
            self.client.subscribe([(self.sub_topic.format(room = room, id = id), 2) for room in self.service.state for id in self.service.state[room]])
            print(f"[MQTT Actuators Control] Subscribed to {[self.sub_topic.format(room = room, id = id) for room in self.service.state for id in self.service.state[room]]}")
        else:
            print(f"[MQTT Actuators Control] Errore di connessione. Codice: {reason_code}")

    def on_message(self, client, userdata, msg):
        """
        Central message parsing dispatcher. Resolves data scopes from topic arrays,
        pipes JSON strings into validation streams, and transmits upstream action confirmations.
        """
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
    # SECTION 5: BRIDGE THREAD LIFE CYCLE MANAGER
    def run(self):
        """
        Main execution driver. Synchronizes with broker discovery routines,
        boots low-level background workers, and safely handles programmatic teardowns.
        """
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