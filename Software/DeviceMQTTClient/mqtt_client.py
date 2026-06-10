# EXERCISE VIII - FIXED MQTT CLIENT
import paho.mqtt.client as mqtt
import json
import time
import threading
import os

from Catalog.mqtt_catalog_client import MQTTCatalogClient

DIR = os.path.dirname(os.path.abspath(__file__))

class DeviceMQTTClient():
    def __init__(self):
        self.config_file = os.path.join(DIR, "network_config.json")

        self.client_id = "DeviceMQTTClient"

        self.cc = MQTTCatalogClient(self.client_id)
        self.registered = False
        
        self.running = True

        self.payload = self._build_payload()

        # Start background refresh thread set to 10 seconds to avoid catalog cleanup expiration
        self.reg_thread = threading.Thread(target=self._registration_loop, daemon=True)
        self.reg_thread.start()

    def _build_payload(self):
        payload_dict = {
            "id": self.client_id,
            "description": "IoT MQTT Client device"
        }
        return payload_dict

    def _registration_loop(self):
        while True:
            time.sleep(self.cc.loop_time)
            if not self.registered:
                if self.cc.register_device(self.payload):
                    self.registered = True
            else:
                if not self.cc.refresh_device(self.client_id):
                    self.registered = False

    def run(self):
        self.cc.connect()

        while self.running:
            try:
                time.sleep(1) # Give the asynchronous threads a brief moment to log initial connection
                print("\n--- MQTT DEVICE MENU ---")
                print("1. Send Manual Registration/Refresh")
                print("2. Show ALL devices inside the Catalog")
                print("3. Search device by custom ID")
                print("4. Exit application")

                choice = input("Select an option: ").strip()

                if choice == "1":
                    res = self.cc.register_device(self.payload)
                    print(json.dumps(res, indent=4))

                elif choice == "2":
                    res = self.cc.get_devices()
                    print(json.dumps(res, indent=4))

                elif choice == "3":
                    device_id = input("Enter target complete device ID: ").strip()
                    if device_id:
                        res = self.cc.get_device(device_id)
                        print(json.dumps(res, indent=4))

                elif choice == "4":
                    self.running = False
                
                else:
                    print("Invalid choice")

            except KeyboardInterrupt:
                break
        
        self.cc.close()
