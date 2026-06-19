# EXERCISE: Exercise 06 / Extension - Smart Home Service Registration
# ACTOR: MQTTLoggerBridge (Dynamic MQTT Telemetry Interceptor)
# DESCRIPTION: Bridges the MQTT network and the Logger web service. It periodically
#              discovers active devices by querying the Catalog, updates its topic
#              subscriptions dynamically, and forwards incoming SenML telemetry
#              directly into the database log processor.

# SECTION 1: SYSTEM ENVIRONMENT & MODULE DEPENDENCIES
import paho.mqtt.client as mqtt
import time
import json
import threading
import os

import SenMLUtils as SenML

DIR = os.path.dirname(os.path.abspath(__file__))
# SECTION 2: CLASS INITIALIZATION & EVENT HOOKING
class MQTTLoggerBridge:
    
    def __init__(self, logger_instance):
        """
        Constructor method. Links the bridge to the main logger context, setups
        the sub-topic trackers, and prepares the asynchronous broker discovery loop.
        """
        self.logger_service = logger_instance
        self.catalog = logger_instance.cc
        self.subscribed_topics = set()
        
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            client_id=f"EventLog_Group12_{int(time.time())}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.broker_valid = threading.Event()
        threading.Thread(target=self._get_broker_connect_loop, daemon=True).start()
    # SECTION 3: DYNAMIC TOPIC DISCOVERY & BROKER CONFIGURATION LOOPS
    def _get_refresh_devices_topics(self):
        """
        Infinite background thread routine. Queries the central Catalog to discover 
        devices, extracts their designated logger topics, and updates subscription lists.
        """
        while True:
            devices = self.catalog.get_devices()
            topics = set()
            for id in devices:
                if "mqtt" in devices[id] and "logger_topic" in devices[id]["mqtt"]:
                    topics.add(devices[id]["mqtt"]["logger_topic"])
            diff = topics.difference(self.subscribed_topics)
            if diff:
                self.client.subscribe([(topic, 2) for topic in diff])
            diff = self.subscribed_topics.difference(topics)
            if diff:
                self.client.unsubscribe([topic for topic in diff])
            self.subscribed_topics = topics
            time.sleep(self.catalog.loop_time)

    def _get_broker_connect_loop(self):
        """
        Queries the network catalog configuration service to extract the core system 
        broker parameters before attempting to establish a server connection socket.
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
                    print(f"[MQTT Logger] Impossibile connettersi al broker su {self.broker_host}:{self.broker_port}")
                self.broker_valid.set()
                break
    # SECTION 4: ASYNCHRONOUS PACKET & NETWORK CONTEXT CALLBACKS
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """
        Callback handler executed upon a connection confirmation request.
        Launches the sub-topic refresh loop if connection reason code is valid.
        """
        if reason_code == 0:
            print(f"[MQTT Logger] Connesso con successo al Broker su {self.broker_host}:{self.broker_port}!")
            threading.Thread(target=self._get_refresh_devices_topics, daemon=True).start()
        else:
            print(f"[MQTT Logger] Errore di connessione. Codice: {reason_code}")

    def on_message(self, client, userdata, msg):
        """
        Inbound packet processor. Intercepts asynchronous event messages, validates 
        the payload formatting against SenML specifications, and appends data into the database.
        """
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            
            # Il Logger intercetta i dati MQTT e li passa al parser SenML
            if SenML.validate_SenML(payload):
                self.logger_service._process_SenML(payload)
                print(f"[MQTT Logger] Evento salvato con successo da {msg.topic}")
            else:
                # Scarta silenziosamente il traffico non SenML (utile se il topic è affollato)
                # print(f"[MQTT Logger - WARN] Messaggio non SenML scartato da {msg.topic}")
                pass
                
        except json.JSONDecodeError:
            print(f"[MQTT Logger - ERROR] Il payload da {msg.topic} non è un JSON valido.")
        except Exception as e:
            print(f"[MQTT Logger - ERROR] Eccezione durante l'elaborazione del messaggio: {e}")
    # SECTION 5: BRIDGE ENGINE THREAD MANAGER
    def run(self):
        """
        Main runner class. Syncs with the broker locator system, launches the
        network background loops, and captures termination hooks for structured clean ups.
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
            self.client.unsubscribe(self.topic)
            self.client.loop_stop()
            self.client.disconnect()
            print("Disconnected")