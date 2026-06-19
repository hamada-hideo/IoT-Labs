# EXERCISE: Exercise 06 / Exercise 09 Extension - Sensor MQTT Telemetry Bridge
# ACTOR: MQTTSensorsBridge (Up-link Data Replication Bridge)
# DESCRIPTION: Bridges incoming HTTP REST sensor measurements over to the MQTT network.
#              It dynamically resolves broker parameters via the Catalog registry,
#              monitors config files for target channels, and mirrors incoming 
#              REST SenML events into a global telemetry topic.

# SECTION 1: SYSTEM ENVIRONMENT & PROTOCOL IMPORT LOGIC
import paho.mqtt.client as mqtt
import time
import json
import threading
import os

import SenMLUtils as SenML

DIR = os.path.dirname(os.path.abspath(__file__))

# SECTION 2: CLASS INITIALIZATION & METADATA OVERLAYS
class MQTTSensorsBridge:
    def __init__(self, service):
        """
        Constructor method. Links the bridge context to the parent REST service,
        parses the fallback topic layouts, and spawns the broker discovery worker.
        """
        self.service = service
        self.catalog = service.cc
        
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            client_id=f"SensorBridge_Group12_{int(time.time())}"
        )
        self.client.on_connect = self.on_connect

        # Legge il topic dal file di configurazione di rete (come fa l'actuators bridge)
        self.config_file = os.path.join(DIR, "network_config.json")
        self.pub_topic = "/tiot/group12/sensors/telemetry" # Fallback sicuro di default
        
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                data = json.load(f)
                if "mqtt" in data and "telemetry_topic" in data["mqtt"]:
                    self.pub_topic = data["mqtt"]["telemetry_topic"]

        self.broker_valid = threading.Event()
        threading.Thread(target=self._get_broker_connect_loop, daemon=True).start()
    # SECTION 3: AUTOMATED BROKER RECOVERY LOOPS
    def _get_broker_connect_loop(self):
        """
        Asynchronous infinite background loop. Periodically queries the central Catalog 
        registry service via REST to dynamically extract and mount broker socket targets.
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
                    print(f"[MQTT Sensors Bridge] Impossibile connettersi al broker su {self.broker_host}:{self.broker_port}")
                self.broker_valid.set()
                break
    # SECTION 4: ASYNCHRONOUS PROTOCOL CALLBACK CHANNELS
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Asynchronous event callback triggered when connection responses return from the broker."""
        if reason_code == 0:
            print(f"[MQTT Sensors Bridge] Connesso con successo al Broker su {self.broker_host}:{self.broker_port}!")
        else:
            print(f"[MQTT Sensors Bridge] Errore di connessione. Codice: {reason_code}")
    # SECTION 5: PROGRAMMATIC OUTBOUND TELEMETRY TRANSMITTERS
    def publish_telemetry(self, senml_data):
        """
        Data duplication endpoint. Explicitly called by the companion HTTP REST server 
        whenever a new measurement POST request is successfully parsed and logged.
        """
        if self.broker_valid.is_set():
            try:
                self.client.publish(self.pub_topic, json.dumps(senml_data))
                print(f"[MQTT Sensors Bridge] Dati pubblicati su {self.pub_topic}")
            except Exception as e:
                print(f"[MQTT Sensors Bridge - ERROR] Fallita pubblicazione: {e}")
    # SECTION 6: BRIDGE RUNTIME MANAGER LOOP
    def run(self):
        """
        Main runner class. Synchronizes with broker discovery routines,
        boots low-level background loops, and captures termination hooks for clean ups.
        """
        self.broker_valid.wait()
        self.running = True
        self.client.loop_start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down Sensor Bridge...")
            self.running = False
            self.client.loop_stop()
            self.client.disconnect()
            print("Disconnected")
