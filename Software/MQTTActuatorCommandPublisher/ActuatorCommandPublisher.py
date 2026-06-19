'''
Develop an MQTT publisher that sends actuation commands to the smart home
actuators (thermostat, lights, blinds) from Exercise 03 and to switch on and off a led
managed the Arduino (refer to Exercise 3.3 Lab Hardware - part 3 for topics and
data format). On startup, this MQTT Actuator Command Publisher queries the Catalog
to discover registered devices and their MQTT command topics. Commands are sent as
JSON (to be defined by your team). The MQTT Actuator Command Publisher also
subscribes to a state-feedback topic to confirm that commands were applied. Implement
an interactive command-line interface for manual control.
This MQTT Actuator Command Pubnlisher must register itself on the Catalog via REST
and keep the registration periodically updated (see Exercise 05)
'''

import paho.mqtt.client as mqtt
import json
import time
import threading

import SenMLUtils as SenML

from Catalog.catalog_client import *

DIR = os.path.dirname(os.path.abspath(__file__))

class ActuatorCommandPublisher():
    def __init__(self):
        self.actuators_config_file = os.path.join(DIR, "actuators_config.json")
        with open(self.actuators_config_file, "r") as f:
            self.rules = json.load(f)
        self.type_map = {
            "bool": lambda x : x.lower() == "true",
            "int": int,
            "float": float
        }
        
        self.catalog = CatalogClient()

        self.client_id = "MQTTActuatorCommandPublisher"

        self.client = mqtt.Client(client_id=f"tiot-group12-{self.client_id}")

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self._get_broker_loop()
        self.client.connect(self.broker_host, self.broker_port)

        self.subscribed_topics = set()
        self.command_topics = {}
        self.devices = {}

        self.payload = self._build_registration_payload()
        self.registered = False
        threading.Thread(target=self._try_register_refresh_loop, daemon=True).start()

        self.running = True

    def _get_refresh_devices_topics(self):
        while True:
            devices = self.catalog.get_devices()
            command_topics = {}
            feedback_topics = set()
            actuators = {}
            for id in devices:
                if "mqtt" in devices[id] and "command_topic" in devices[id]["mqtt"]:
                    command_topics[id] = devices[id]["mqtt"]["command_topic"]
                    actuators[id] = devices[id]
                    if "feedback_topic" in devices[id]["mqtt"]:
                        feedback_topics.add(devices[id]["mqtt"]["feedback_topic"])
            diff = feedback_topics.difference(self.subscribed_topics)
            if diff:
                self.client.subscribe([(topic, 2) for topic in diff])
            diff = self.subscribed_topics.difference(feedback_topics)
            if diff:
                self.client.unsubscribe([topic for topic in diff])
            self.devices = actuators
            self.command_topics = command_topics
            self.subscribed_topics = feedback_topics
            time.sleep(self.catalog.loop_time)

    def _try_register_refresh_loop(self):
        while True:
            time.sleep(self.catalog.loop_time)
            if not self.registered:
                if self.catalog.register_service(self.payload):
                    self.registered = True
                    print(f"[{time.strftime('%X')}] Registration successful for {self.client_id}")
            else:
                if not self.catalog.refresh_service(self.client_id):
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

    def on_connect(self,client, userdata,flags,rc):
        if rc == 0:
            print("Connected successfully.")
            threading.Thread(target=self._get_refresh_devices_topics, daemon=True).start()
        else:
            print(f"Connection failed with error code {rc}")
            return

    def on_message(self,client,userdata,msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            print(f"Malformed feedback received on {topic}")
            return
        print(f"FEEDBACK received on {msg.topic}: {data}")

    def _build_registration_payload(self):
        return{
            "id" : self.client_id,
            "description" : "MQTT Actuator Command Publisher"
        }

    def _send_command(self, topic, payload):
        message = json.dumps(payload)
        self.client.publish(topic,message)
        print(f"[{time.strftime('%X')}] Command sent to {topic}: {payload}")

    def run(self):
        self.client.loop_start()
        print(f"[{time.strftime('%X')}] Actuator Command Publisher started")
        while self.running:
            try:
                if self.devices:
                    print("\n--- MQTT PUBLISHER ---")

                    print(f"Select actuator {[actuator for actuator in self.devices]}:")
                    actuator = input(">")
                    if actuator not in self.devices:
                        print("Invalid choice")
                        continue

                    actuator_type = self.devices[actuator]["resources"]["type"]

                    print(f"Insert the value for actuator {actuator}:")
                    value = input("> ")
                    self._send_command(
                        self.command_topics[actuator],
                        SenML.build_array_dict([SenML.build_event_dict(
                            f"smart_home/{actuator}",
                            self.rules[actuator_type]["unit"],
                            self.type_map[self.rules[actuator_type]["value_type"]](value),
                            time.time()
                        )])
                    )
                else:
                    print("No actuators online")
                    time.sleep(self.catalog.loop_time)

            except KeyboardInterrupt:
                print("Shutting down...")
                self.running = False
                self.client.unsubscribe([
                    self.feedback_topic.format(room = room, id = id) for room in self.devices for id in self.devices[room]
                ])
                self.client.loop_stop()
                self.client.disconnect()
                print("Disconnected")
