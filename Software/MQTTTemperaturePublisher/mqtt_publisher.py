import paho.mqtt.client as mqtt
import json
import time
import threading
import random
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from Catalog.catalog_client import CatalogClient
import SenMLUtils as SenML

DIR = os.path.dirname(os.path.abspath(__file__))

class TemperaturePublisher():
    def __init__(self):
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.ip = data["ip"]
        self.port = data["port"]

        self.publish_interval = 30
        self.publish_topic = data["publish_topic"]
        self.command_topic = data["command_topic"]
        self.catalog = CatalogClient()

        self.client_id = "TemperaturePublisher"

        self.client = mqtt.Client(client_id=f"tiot-group12-{self.client_id}")

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self._get_broker_loop()
        self.client.connect(self.broker_host, self.broker_port)

        self.payload = self._build_registration_payload()
        self.registered = False
        threading.Thread(target=self._try_register_refresh_loop, daemon=True).start()

        self.running = True

        self.pub_thread = threading.Thread(target=self._publish_loop, daemon=True)
        self.pub_thread.start()

    def _try_register_refresh_loop(self):
        while True:
            time.sleep(self.catalog.loop_time)
            if not self.registered:
                if self.catalog.register_device(self.payload):
                    self.registered = True
                    print(f"[{time.strftime('%X')}] Registration successful for {self.client_id}")
            else:
                if not self.catalog.refresh_device(self.client_id):
                    self.registered = False
                    print(f"[{time.strftime('%X')}] Refresh failed, retrying next cycle")
                else:
                    print(f"[{time.strftime('%X')}] Registration refreshed for {self.client_id}")

    def _get_broker_loop(self):
        while True:
            time.sleep(self.catalog.loop_time)
            broker = self.catalog.get_broker()
            if broker:
                self.broker_host = broker["ip"]
                self.broker_port = broker["port"]
                break

    def on_connect(self,client,userdata,flags,rc):
        if rc == 0:
            print("Connected successfully")
        else:
            print(f"Connection failed with code: {rc}")
            return
        self.client.subscribe(self.command_topic)
        print(f"Subscribed to {self.command_topic}")

    def on_message(self,client,userdata,msg):
        payload = msg.payload.decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            print(f"Malformed message received on {msg.topic}")
            return

        if "interval" in data:
            self.publish_interval = data["interval"]
            print(f"Publish interval updated to {self.publish_interval} seconds")
        else:
            print(f"Unknown command received: {data}")

    def _build_registration_payload(self):
        return {
        "id": self.client_id,
        "description": "MQTT Temperature Sensor",
        "mqtt": {
            "broker": {
                "ip": self.broker_host,
                "port": self.broker_port
            },
            "sub_topics": [self.command_topic],
            "pub_topics": [self.publish_topic]
        },
        "resources": ["temperature"]
    }

    def _build_senml(self,temperature):
        return json.dumps(
            SenML.build_array_dict([
                SenML.build_event_dict(
                    f"smart_home/{self.client_id}/temperature", 
                    "Cel", 
                    temperature, 
                    time.time()
                )
            ])
        )

    def _publish_loop(self):
        while self.running:
            temperature = round(random.uniform(20.0, 30.0),2)
            payload = self._build_senml(temperature)

            self.client.publish(self.publish_topic, payload)
            print(f"Published temperature: {temperature} Cel")

            time.sleep(self.publish_interval)

    def run(self):
        self.client.loop_start()
        print(f"[{time.strftime('%X')}] Temperature publisher started")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
            self.running = False
            self.client.loop_stop()
            self.client.unsubscribe(self.command_topic)
            self.client.disconnect()
            print("Disconnected")
