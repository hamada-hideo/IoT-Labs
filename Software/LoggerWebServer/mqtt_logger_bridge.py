import paho.mqtt.client as mqtt
import time
import json
import threading
import os

import SenMLUtils as SenML

DIR = os.path.dirname(os.path.abspath(__file__))

class MQTTLoggerBridge:
    def __init__(self, logger_instance):
        self.logger_service = logger_instance
        self.catalog = logger_instance.cc
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            self.topic = json.load(f)["mqtt"]["sub_topic"]
        
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            client_id=f"EventLog_Group12_{int(time.time())}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

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
                    print(f"[MQTT Logger] Impossibile connettersi al broker su {self.broker_host}:{self.broker_port}")
                self.broker_valid.set()
                break

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[MQTT Logger] Connesso con successo al Broker su {self.broker_host}:{self.broker_port}!")
            self.client.subscribe(self.topic)
        else:
            print(f"[MQTT Logger] Errore di connessione. Codice: {reason_code}")

    def on_message(self, client, userdata, msg):
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
            self.client.unsubscribe(self.topic)
            self.client.loop_stop()
            self.client.disconnect()
            print("Disconnected")