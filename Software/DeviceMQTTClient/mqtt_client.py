# EXERCISE VIII - FIXED MQTT CLIENT
import paho.mqtt.client as mqtt
import json
import time
import threading
import os

DIR = os.path.dirname(os.path.abspath(__file__))

class DeviceMQTTClient():
    def __init__(self):
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.ip = data["ip"]
        self.port = data["port"]
        self.broker_ip = data["broker"]["ip"]
        self.broker_port = data["broker"]["port"]

        self.client_id = "DeviceMQTTClient"
        self.client = mqtt.Client(client_id=f"tiot-group12-{self.client_id}")
        self.running = True

        # Assign MQTT callback functions
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Define standard topic structure aligned with the catalog bridge
        self.register_topic = "/tiot/group12/catalog/register"
        self.ack_topic = f"/tiot/group12/catalog/ack/{self.client_id}"
        self.query_request_topic = "/tiot/group12/catalog/query/request"
        self.query_response_topic = "/tiot/group12/catalog/query/response"

        self.payload = self._build_payload()

        self.client.connect(self.broker_ip, self.broker_port)

        # Start background refresh thread set to 10 seconds to avoid catalog cleanup expiration
        self.reg_thread = threading.Thread(target=self._registration_loop, daemon=True)
        self.reg_thread.start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("\n[MQTT] Successfully connected to the Broker!")
            # Subscribe to acknowledgement and response channels
            self.client.subscribe(self.ack_topic)
            self.client.subscribe(self.query_response_topic)
        else:
            print(f"[MQTT] Connection failed. Error code: {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))

            if topic == self.ack_topic:
                print(f"\n<<< [ACK RECEIVED]: {payload['message']}")

            elif topic == self.query_response_topic:
                print("\n============= CATALOG QUERY RESULT =============")
                print(json.dumps(payload, indent=4))
                print("================================================\n")
        except Exception as e:
            print(f"\n[Message Decode Error]: {e}")

    def _build_payload(self):
        payload_dict = {
            "id": self.client_id,
            "description": "IoT MQTT Client device",
            "mqtt": {
                "ip": self.ip,
                "port": self.port,
                "sub_topics": [
                    self.ack_topic,
                    self.query_request_topic
                ],
                "pub_topics": [
                    self.register_topic,
                    self.query_response_topic
                ]
            }
        }
        return json.dumps(payload_dict)

    def _registration_loop(self):
        while self.running:
            self.client.publish(self.register_topic, self.payload)
            # Keeping it down to 10 seconds beats the catalog's background cleanup loop
            time.sleep(5)

    def run(self):
        self.client.loop_start()

        while self.running:
            time.sleep(1) # Give the asynchronous threads a brief moment to log initial connection
            print("\n--- MQTT DEVICE MENU ---")
            print("1. Send Manual Registration/Refresh")
            print("2. Show ALL devices inside the Catalog")
            print("3. Search device by custom ID")
            print("4. Exit application")

            choice = input("Select an option: ").strip()

            if choice == "1":
                self.client.publish(self.register_topic, self.payload)
                print(">>> Registration request sent to catalog.")

            elif choice == "2":
                # FIXED: Publishes to the REQUEST topic channel, not the response loopback
                query = {"action": "get_devices"}
                self.client.publish(self.query_request_topic, json.dumps(query))
                print(">>> Fetching all records from catalog...")

            elif choice == "3":
                device_id = input("Enter target complete device ID: ").strip()
                if device_id:
                    # FIXED: Publishes to the REQUEST topic channel, not the response loopback
                    query = {"action": "get_device_by_id", "id": device_id}
                    self.client.publish(self.query_request_topic, json.dumps(query))
                    print(f">>> Search query for ID '{device_id}' sent...")

            elif choice == "4":
                self.running = False
                self.client.loop_stop()
                self.client.disconnect()
                print("Disconnected. Goodbye!")
            
            else:
                print("Invalid choice")
