# EXERCISE: Exercise 07 - IoT Catalog - MQTT Extension
# ACTOR: MQTTCatalogBridge (MQTT Interface for the Catalog)
# DESCRIPTION: Manages the MQTT communication layer of the IoT Catalog. It handles
#              asynchronous device/service registration, keep-alive updates (refresh),
#              and dispatches incoming interactive database queries via MQTT topics.

# SECTION 1: SYSTEM IMPORTS AND DEPENDENCIES
# System and time utilities alongside core JSON processing structures
import sys
import os
import json
import time
import paho.mqtt.client as mqtt

# Importiamo la classe Catalog dal vostro file catalog_service.py
from catalog_service import Catalog

DIR = os.path.dirname(os.path.abspath(__file__))
# SECTION 2: CLASS INITIALIZATION AND NETWORK CONFIGURATION
class MQTTCatalogBridge:
    def __init__(self, catalog_instance):
        """
        Constructor method. Couples the bridge with the central Catalog database instance,
        loads MQTT topics from configuration files, and establishes the connection to the broker.
        """
        # Maintain a pointer to the main Catalog memory object for shared data access
        self.catalog_service = catalog_instance

        # Instantiate the MQTT Client and bind asynchronous event callbacks
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        # Load dynamic communication topics from network config file to prevent hardcoded paths
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        
        self.registration_topic = data["mqtt"]["register_topic"]
        self.query_request_topic = data["mqtt"]["query_request_topic"]
        self.query_response_topic = data["mqtt"]["query_response_topic"]
        self.generic_ack_topic = data["mqtt"]["ack_topic"]

        # Extract broker connectivity parameters dynamically from the existing Catalog dictionary
        self.broker_ip = self.catalog_service.catalog["broker"]["ip"]
        self.broker_port = self.catalog_service.catalog["broker"]["port"]
        # Safe initialization attempt to connect to the configured network broker
        try:
            self.client.connect(self.broker_ip, self.broker_port, 60)
        except:
            print(f"[MQTT] Impossibile connettersi al broker su {self.broker_ip}:{self.broker_port}")
        self.running = True

    # SECTION 3: MQTT EVENT CALLBACKS
    def on_connect(self, client, userdata, flags, rc):
        """
        Event handler automatically triggered when the client receives a connection response from the broker.
        """
        if rc == 0:
            self.client.subscribe(self.query_request_topic)
            print(f"[MQTT] Connesso con successo al Broker su {self.broker_ip}:{self.broker_port}!")
            # Subscribe to the query topic to handle interactive entity data requests
            self.client.subscribe(self.registration_topic)
            # Subscribe to the registration topic to catch device and service heartbeats
            print(f"[MQTT] Iscritto al topic di registrazione: {self.registration_topic}")
        else:
            print(f"[MQTT] Errore di connessione. Codice: {rc}")

    def on_message(self, client, userdata, msg):
        """
        Central message dispatcher triggered when a packet is published on any subscribed topic.
        """
        try:
           # Decode the raw string payload and parse the nested JSON content
            payload = json.loads(msg.payload.decode("utf-8"))
            print(f"\n[MQTT] Ricevuto messaggio su {msg.topic}: {payload}")

            # Route payloads to their designated handler subroutines based on incoming topic names
            if msg.topic == self.query_request_topic:
                self._handle_query(payload)
            elif msg.topic == self.registration_topic:
                self._handle_registration(payload)
        except json.JSONDecodeError:
            print("[MQTT] Errore: Il messaggio ricevuto non è in un formato JSON valido.")
        except Exception as e:
            print(f"[MQTT] Errore durante l'elaborazione del messaggio: {e}")
    # SECTION 4: THREAD EXECUTION LOOP & CLEAN DISCONNECT
    def run(self):
        """
        Starts the internal non-blocking network background loop and monitors execution context.
        """
        self.client.loop_start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
            self.running = False

            # Clean teardown: stop loops, unsubscribe from network layers, and cleanly disconnect
            self.client.loop_stop()
            self.client.unsubscribe([self.registration_topic, self.query_request_topic])
            self.client.disconnect()
            print("Disconnected")


    # SECTION 5: DISPATCH SUBROUTINES (QUERY & REGISTRATION LOGIC)
    def _handle_query(self, payload):
        """
        Processes interactive reading requests submitted over the query request topic and 
        returns the target slice of the catalog data back to the requester.
        """
        action = payload.get("action")
        request_id = payload.get("request_id")
        # Thread-safe read evaluation using the core class resource lock
        with self.catalog_service.lock:
            if action == "get_all":
                result = {
                    "data": self.catalog_service.catalog
                }
            elif action == "get_devices":
                result = {
                    "data": self.catalog_service.catalog["devices"]
                }
            elif action == "get_services":
                result = {
                    "data": self.catalog_service.catalog["services"]
                }
            elif action == "get_device_by_id":
                device_id = payload.get("id")
                if not device_id:
                    result = {"error": "id not found"}
                else:
                    result = {
                        "data": self.catalog_service.catalog["devices"].get(device_id, {"error": "not found"})
                    }
            elif action == "get_service_by_id":
                service_id = payload.get("id")
                if not service_id:
                    result = {"error": "id not found"}
                else:
                    result = {
                        "data": self.catalog_service.catalog["services"].get(service_id, {"error": "not found"})
                    }
            else:
                result = {"error": "unknown action"}

        # Append transactional tracking IDs to tie async responses to corresponding request blocks
        if request_id and "error" not in result:
            result["request_id"] = request_id
        # Publish query execution output to the designated global query response channel    
        self.client.publish(self.query_response_topic, json.dumps(result))
        print(f"[MQTT] Query response inviata su {self.query_response_topic}")

    def _handle_registration(self, payload):
        """
        Processes entity registration or refresh events. Inserts or modifies data dictionaries 
        within protected blocks and triggers a physical system save.
        """

        # Validate data classification scope
        category = payload.get("category")
        if category not in ["devices", "services"]:
            print("[MQTT] Errore: Categoria non valida. Usa 'devices' o 'services'")
            return

        item_id = payload.get("id")
        if not item_id:
            print("[MQTT] Errore: Il payload non contiene un 'id'")
            return
        
        request_id = payload.get("request_id")

        # Mutex-locked section to prevent synchronization anomalies during disk modifications
        with self.catalog_service.lock:
            if item_id in self.catalog_service.catalog[category]:
                # Perform an entry update if structural payload data is present, otherwise execute simple keep-alive
                if "data" in payload:
                    payload["data"]['insert_timestamp'] = time.time()
                    self.catalog_service.catalog[category][item_id] = payload["data"]
                else:
                    self.catalog_service.catalog[category][item_id]['insert_timestamp'] = time.time()
                print(f"[MQTT] Refresh effettuato per {item_id}")
            else:
                # Handle full initialization registration for new client entries
                if "data" in payload:
                    payload["data"]['insert_timestamp'] = time.time()
                    self.catalog_service.catalog[category][item_id] = payload["data"]
                    print(f"[MQTT] Nuovo {category[:-1]} registrato con successo via MQTT")
                else:
                    print(f"[MQTT] Errore durante la registrazione: campo 'data' non presente")
            # Commit changes to disk storage
            self.catalog_service._save_catalog()

        # Generate target confirmation routing token (ACK) by injecting the entity identifier
        response_topic = self.generic_ack_topic.replace("<id>", item_id)
        ack_message = {
            "data": {
                "status": "success",
                "message": f"Registrazione/Refresh di {item_id} elaborata dal Catalogo."
            }
        }
        if request_id:
            ack_message["request_id"] = request_id
        # Publish downstream confirmation flag to notifying clients
        self.client.publish(response_topic, json.dumps(ack_message))
        print(f"[MQTT] ACK inviato sul topic: {response_topic}")
