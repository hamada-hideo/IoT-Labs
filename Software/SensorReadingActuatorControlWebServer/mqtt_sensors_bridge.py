import paho.mqtt.client as mqtt
import time
import json
import threading
import os

import SenMLUtils as SenML

DIR = os.path.dirname(os.path.abspath(__file__))

class MQTTSensorsBridge:
    def __init__(self, service):
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

    def _get_broker_connect_loop(self):
        """Ciclo di attesa per trovare il broker interrogando il catalogo"""
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

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[MQTT Sensors Bridge] Connesso con successo al Broker su {self.broker_host}:{self.broker_port}!")
        else:
            print(f"[MQTT Sensors Bridge] Errore di connessione. Codice: {reason_code}")

    def publish_telemetry(self, senml_data):
        """Metodo chiamato dal server REST per clonare il dato su MQTT"""
        if self.broker_valid.is_set():
            try:
                self.client.publish(self.pub_topic, json.dumps(senml_data))
                print(f"[MQTT Sensors Bridge] Dati pubblicati su {self.pub_topic}")
            except Exception as e:
                print(f"[MQTT Sensors Bridge - ERROR] Fallita pubblicazione: {e}")

    def run(self):
        """Avvia il loop asincrono MQTT in un thread parallelo"""
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
