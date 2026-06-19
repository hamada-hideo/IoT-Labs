# EXERCISE: Exercise 08 - IoT Catalog - MQTT Device Client
# ACTOR: DeviceMQTTClient (Interactive Device Emulator)
# DESCRIPTION: Emulates an active IoT device node. It launches a background loop
#              thread to maintain automated registration/refresh intervals and
#              provides a terminal CLI menu to trigger interactive queries.
# SECTION 1: SYSTEM ENVIRONMENT & MODULE IMPORTS
import paho.mqtt.client as mqtt
import json
import time
import threading
import os

from Catalog.mqtt_catalog_client import MQTTCatalogClient

DIR = os.path.dirname(os.path.abspath(__file__))
# SECTION 2: CLASS INITIALIZATION & CONTEXT SETUP
class DeviceMQTTClient():
    def __init__(self):
        """
        Constructor method. Initializes client naming scopes, builds the entry
        payload, and spawns the background periodic registration lifecycle thread.
        """

        self.client_id = "DeviceMQTTClient"

        self.cc = MQTTCatalogClient(self.client_id)
        self.registered = False
        
        self.running = True

        self.payload = self._build_payload()

        # Start background refresh thread set to 10 seconds to avoid catalog cleanup expiration
        self.reg_thread = threading.Thread(target=self._registration_loop, daemon=True)
        self.reg_thread.start()
    # SECTION 3: PAYLOAD CONSTRUCTION & BACKGROUND MAINTENANCE LOOPS
    def _build_payload(self):
        """
        Internal helper method to construct the initial data payload format required 
        by the Catalog registry database scheme.
        """
        payload_dict = {
            "id": self.client_id,
            "description": "IoT MQTT Client device"
        }
        return payload_dict

    def _registration_loop(self):
        """
        Asynchronous infinite loop handling automated cloud presence management. 
        Alternates between initial POST registrations and keep-alive refreshes.
        """
        while True:
            time.sleep(self.cc.loop_time)
            if not self.registered:
                if self.cc.register_device(self.payload):
                    self.registered = True
            else:
                if not self.cc.refresh_device(self.client_id):
                    self.registered = False
    # SECTION 4: INTERACTIVE CLI USER INTERFACE (RUN LOOP)
    def run(self):
        """
        Main execution thread. Establishes broker linkage and boots up the interactive
        CLI menu loop to handle live user query triggers over the network.
        """
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
                # Option 1: Trigger immediate synchronous registration request
                if choice == "1":
                    res = self.cc.register_device(self.payload)
                    print(json.dumps(res, indent=4))
                # Option 2: Dispatch query request to view all devices inside the database
                elif choice == "2":
                    res = self.cc.get_devices()
                    print(json.dumps(res, indent=4))
                # Option 3: Search a single device record by dynamically providing its ID
                elif choice == "3":
                    device_id = input("Enter target complete device ID: ").strip()
                    if device_id:
                        res = self.cc.get_device(device_id)
                        print(json.dumps(res, indent=4))
                # Option 4: Halt execution flow and trigger programmatic cleanup shutdown
                elif choice == "4":
                    self.running = False
                
                else:
                    print("Invalid choice")

            except KeyboardInterrupt:
                break
        
        self.cc.close()
