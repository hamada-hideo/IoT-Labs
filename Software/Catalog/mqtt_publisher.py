import paho.mqtt.client as mqtt
import json
import time
import threading
import random
from catalog_client import CatalogClient

HOST = "broker.hivemq.com"
PORT = 1883
PUBLISH_TOPIC = "/tiot/group12/temperature"
COMMAND_TOPIC = "/tiot/group12/temperature/config"

class TemperaturePublisher():
    def __init__(self):
        self.catalog = CatalogClient("localhost", 8080, "catalog")
        broker = self.catalog.get_broker()
        if not broker:
            raise RuntimeError("Could not reach Catalog — check if running")

        self.broker_host = broker["ip"]
        self.broker_port = broker["port"]

        self.client_id = "temp_sensor_001"
        self.client = mqtt.Client(client_id=self.client_id)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.publish_interval = 30
        self.running = True

        self.client.connect(self.broker_host,self.broker_port)
        self.catalog.register_device(self._build_registration_payload())

        self.pub_thread = threading.Thread(target=self._publish_loop, daemon=True)
        self.pub_thread.start()

        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()



    def on_connect(self,client,userdata,flags,rc):
        if rc == 0:
            print("Connected successfully")
        else:
            print(f"Connection failed with code: {rc}")
            return
        self.client.subscribe(COMMAND_TOPIC)
        print(f"Subscribed to {COMMAND_TOPIC}")

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
        "endpoint": None,
        "mqtt": {
            "ip": self.broker_host,
            "port": self.broker_port,
            "topic": PUBLISH_TOPIC
        },
        "resources": ["temperature"],
        "insert_timestamp": time.time()
    }

    def _build_senml(self,temperature):
        senml = [
            {
                "bn" : f"iot/group12/sensor/{self.client_id}/",
                "bt" : time.time(),
                "bu" : "Cel"
            },

            {
                "n" : "temperature",
                "v" : temperature
            }
        ]

        return json.dumps(senml)

    def _publish_loop(self):
        while self.running:
            temperature = round(random.uniform(20.0, 30.0),2)
            payload = self._build_senml(temperature)

            self.client.publish(PUBLISH_TOPIC, payload)
            print(f"Published temperature: {temperature} Cel")

            time.sleep(self.publish_interval)


    def _refresh_loop(self):
        while self.running:
            result = self.catalog.refresh_device(self.client_id)
            if result:
                print(f"[{time.strftime('%X')}] Registration refreshed for {self.client_id}")
            else:
                print(f"[{time.strftime('%X')}] Refresh failed, retrying next cycle")
            time.sleep(10)

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
            self.client.disconnect()
            print("Disconnected")


if  __name__ == "__main__":
    publisher = TemperaturePublisher()
    publisher.run()
