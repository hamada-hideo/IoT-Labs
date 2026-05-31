'''
Develop an MQTT publisher that sends actuation commands to the smart home
actuators (thermostat, lights, blinds) from Exercise 03 and to switch on and off a led
managed the Arduino (refer to Exercise 3.3 Lab Hardware – part 3 for topics and
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
import random
from CatalogClient import CatalogClient

HOST = "broker.hivemq.com"
PORT = 1883

TEMPERATURE_FEEDBACK_TOPIC = "/tiot/group12/temperature/state"
LIGHTS_FEEDBACK_TOPIC = "/tiot/group12/lights/state"
BLINDS_FEEDBACK_TOPIC = "/tiot/group12/blinds/state"
LED_FEEDBACK_TOPIC = "/tiot/group12/led/state"

TEMPERATURE_COMMAND_TOPIC = "/tiot/group12/temperature/config"
LIGHTS_COMMAND_TOPIC = "/tiot/group12/lights/config"
BLINDS_COMMAND_TOPIC = "/tiot/group12/blinds/config"
LED_COMMAND_TOPIC = "/tiot/group12/led/config"

class ActuatorCommandPublisher():
    def __init__(self):
        self.catalog = CatalogClient("localhost", 8080, "catalog")
        broker = self.catalog.get_broker()
        if not broker:
            raise RuntimeError("Could not reach the catalog - check if running")

        self.broker_host = broker["ip"]
        self.broker_port = broker["port"]

        self.client_id = "actuator_publisher_001"
        self.client = mqtt.Client(client_id=self.client_id)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.running = True

        self.client.connect(self.broker_host, self.broker_port)
        self.catalog.register_device(self._build_registration_payload())

        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()

    def on_connect(self,client, userdata,flags,rc):
        if rc == 0:
            print("Connected successfully.")
        else:
            print(f"Connection failed with error code {rc}")
            return
        self.client.subscribe(TEMPERATURE_FEEDBACK_TOPIC)
        self.client.subscribe(LED_FEEDBACK_TOPIC)
        self.client.subscribe(BLINDS_FEEDBACK_TOPIC)
        self.client.subscribe(LIGHTS_FEEDBACK_TOPIC)
        print(f"Subscribed to {TEMPERATURE_FEEDBACK_TOPIC}")
        print(f"Subscribed to {LED_FEEDBACK_TOPIC}")
        print(f"Subscribe to {BLINDS_FEEDBACK_TOPIC}")
        print(f"Subscribe to {LIGHTS_FEEDBACK_TOPIC}")

    def _build_registration_payload(self):
        return{
            "id" : self.client_id,
            "description" : "MQTT Actuator Command Publisher",
            "endpoint": None,
            "mqtt": {
                "ip": self.broker_host,
                "port": self.broker_port,
                "topics": {
                    "commands": [
                        TEMPERATURE_COMMAND_TOPIC,
                        LIGHTS_COMMAND_TOPIC,
                        BLINDS_COMMAND_TOPIC,
                        LED_COMMAND_TOPIC
                    ],
                    "feedback":[
                        TEMPERATURE_FEEDBACK_TOPIC,
                        LIGHTS_FEEDBACK_TOPIC,
                        BLINDS_FEEDBACK_TOPIC,
                        LED_FEEDBACK_TOPIC
                    ]
                }
            },
            "resources": ["thermostat","lights","blinds","led"],
            "insert_timestamp": time.time()
        }

    def _refresh_loop(self):
        while self.running:
            result = self.catalog.refresh_device(self.client_id)
            if result:
                print(f"[{time.strftime('%X')}] Registration refreshedw for {self.client_id}")
            else:
                print(f"[{time.strftime('%X')}] Refresh failed, retrying next cycle")
            time.sleep(60)


    def on_message(self,client,userdata,msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            print(f"Malformed feedback received on {topic}")
            return
        if topic == TEMPERATURE_FEEDBACK_TOPIC:
            print(f"[THERMOSTAT FEEDBACK] {data}")
        elif topic == LIGHTS_FEEDBACK_TOPIC:
            print(f"[LIGHTS FEEDBACK] {data}")
        elif topic == BLINDS_FEEDBACK_TOPIC:
            print(f"[BLINDS FEEDBACK] {data}")
        elif topic == LED_FEEDBACK_TOPIC:
            print(f"[LED FEEDBACK] {data}")
        else:
            print(f"[UNKNOWN FEEDBACK] topic: {topic} - {data}")

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
                print("3. Send commands to the lights")
                print("4. Send command to the LED")

                choice = input("Select an option: ").strip()

                if choice == "1":
                    temp = input("Enter target temperature (Celsius degrees):").strip()
                    self._send_command(TEMPERATURE_COMMAND_TOPIC,{"temperature": float(temp)})

                elif choice == "2":
                    status = input("Lights on or off? (on/off):").strip()
                    self._send_command(LIGHTS_COMMAND_TOPIC, {"status": status})

                elif choice == "3":
                    position = input("Enter blinds position (0-100): ").strip()
                    self._send_command(BLINDS_COMMAND_TOPIC, {"position": int(position)})
                elif choice == "4":
                    status = input("LED on or off? (on/off): ").strip()
                    self._send_command(LED_COMMAND_TOPIC, {"status":status})

                elif choice == "5":
                    self.running = False
                    self.client.loop_stop()
                    self.client.disconnect()
                    print("Disconnected")
                else:
                    print("Invalid option,try again.")

            except KeyboardInterrupt:
                print("Shutting down...")
                self.running = False
                self.client.loop_stop()
                self.client.disconnect()
                print("Disconnected")

if __name__ == "__main__":
    publisher = ActuatorCommandPublisher()
    publisher.run()


