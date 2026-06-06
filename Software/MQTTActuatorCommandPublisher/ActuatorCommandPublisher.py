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

from Catalog.catalog_client import *

DIR = os.path.dirname(os.path.abspath(__file__))

class ActuatorCommandPublisher():
    def __init__(self):
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.temperature_feedback_topic = data["temperature_feedback_topic"]
        self.lights_feedback_topic = data["lights_feedback_topic"]
        self.blinds_feedback_topic = data["blinds_feedback_topic"]
        self.led_feedback_topic = data["led_feedback_topic"]
        self.temperature_command_topic = data["temperature_command_topic"]
        self.lights_command_topic = data["lights_command_topic"]
        self.blinds_command_topic = data["blinds_command_topic"]
        self.led_command_topic = data["led_command_topic"]
        
        self.catalog = CatalogClient()

        self.client_id = "MQTTActuatorCommandPublisher"

        self.client = mqtt.Client(client_id=self.client_id)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self._get_broker_loop()
        self.client.connect(self.broker_host, self.broker_port)

        self.payload = self._build_registration_payload()
        self.registered = False
        threading.Thread(target=self._try_register_refresh_loop, daemon=True).start()

        self.running = True

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

    def on_connect(self,client, userdata,flags,rc):
        if rc == 0:
            print("Connected successfully.")
        else:
            print(f"Connection failed with error code {rc}")
            return
        self.client.subscribe([
            (self.temperature_feedback_topic, 2), 
            (self.lights_feedback_topic, 2), 
            (self.blinds_feedback_topic, 2), 
            (self.led_feedback_topic, 2)
        ])
        print(f"Subscribed to feedback topics: {self.temperature_feedback_topic}, {self.lights_feedback_topic}, {self.blinds_feedback_topic}, {self.led_feedback_topic}")

    def on_message(self,client,userdata,msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            print(f"Malformed feedback received on {topic}")
            return
        if topic == self.temperature_feedback_topic:
            print(f"[THERMOSTAT FEEDBACK] {data}")
        elif topic == self.lights_feedback_topic:
            print(f"[LIGHTS FEEDBACK] {data}")
        elif topic == self.blinds_feedback_topic:
            print(f"[BLINDS FEEDBACK] {data}")
        elif topic == self.led_feedback_topic:
            print(f"[LED FEEDBACK] {data}")
        else:
            print(f"[UNKNOWN FEEDBACK] topic: {topic} - {data}")

    def _build_registration_payload(self):
        return{
            "id" : self.client_id,
            "description" : "MQTT Actuator Command Publisher",
            "mqtt": {
                "broker": {
                    "ip": self.broker_host,
                    "port": self.broker_port
                },
                "topics": {
                    "commands": [
                        self.temperature_command_topic,
                        self.lights_command_topic,
                        self.blinds_command_topic,
                        self.led_command_topic
                    ],
                    "feedback":[
                        self.temperature_feedback_topic,
                        self.lights_feedback_topic,
                        self.blinds_feedback_topic,
                        self.led_feedback_topic
                    ]
                }
            },
            "resources": ["thermostat","lights","blinds","led"]
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
                print("\n--- MQTT PUBLISHER MENU ---")
                print("1. Send command to the thermostat")
                print("2. Send command to the blinds")
                print("3. Send command to the lights")
                print("4. Send command to the LED")

                choice = input("Select an option: ").strip()

                if choice == "1":
                    temp = input("Enter target temperature (Celsius degrees):").strip()
                    self._send_command(self.temperature_command_topic,{"temperature": float(temp)})

                elif choice == "2":
                    status = input("Lights on or off? (on/off):").strip()
                    self._send_command(self.lights_command_topic, {"status": status})

                elif choice == "3":
                    position = input("Enter blinds position (0-100): ").strip()
                    self._send_command(self.blinds_command_topic, {"position": int(position)})
                elif choice == "4":
                    status = input("LED on or off? (on/off): ").strip()
                    self._send_command(self.led_command_topic, {"status":status})

                elif choice == "5":
                    self.running = False
                    self.client.unsubscribe([
                        self.temperature_feedback_topic, 
                        self.lights_feedback_topic, 
                        self.blinds_feedback_topic, 
                        self.led_feedback_topic
                    ])
                    self.client.loop_stop()
                    self.client.disconnect()
                    print("Disconnected")
                else:
                    print("Invalid option,try again.")

            except KeyboardInterrupt:
                print("Shutting down...")
                self.running = False
                self.client.unsubscribe([
                    self.temperature_feedback_topic, 
                    self.lights_feedback_topic, 
                    self.blinds_feedback_topic, 
                    self.led_feedback_topic
                ])
                self.client.loop_stop()
                self.client.disconnect()
                print("Disconnected")
