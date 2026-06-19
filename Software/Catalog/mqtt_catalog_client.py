# EXERCISE: Exercise 08 - IoT Catalog - MQTT Device Client
# ACTOR: MQTTCatalogClient (MQTT Client Wrapper for IoT Devices/Services)
# DESCRIPTION: Implements a synchronous Request-Response pattern over MQTT.
#              Enables endpoints to register, update keep-alive timestamps,
#              and query the central catalog using dynamic thread event synchronization.


# SECTION 1: SYSTEM IMPORTS AND CORE EXTENSIONS
import json
import os
import time
import paho.mqtt.client as mqtt
import threading
import uuid

DIR = os.path.dirname(os.path.abspath(__file__))
# SECTION 2: CLASS INITIALIZATION AND CONTEXT DEFINITION
class MQTTCatalogClient:
    
    def __init__(self, id):
        """
        Constructor method. Initializes target subscription and routing topics,
        configures a unique MQTT Client ID to avoid broker collisions, and sets up sync structures.
        """
        self.config_file = os.path.join(DIR, "config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.broker_ip = data["mqtt"]["broker"]["ip"]
        self.broker_port = data["mqtt"]["broker"]["port"]
        self.register_topic = data["mqtt"]["register_topic"]
        self.ack_topic = data["mqtt"]["ack_topic"].replace("<id>", id)
        self.query_request_topic = data["mqtt"]["query_request_topic"]
        self.query_response_topic = data["mqtt"]["query_response_topic"]
        self.loop_time = data["expiration_time"] // 2

        # Unique client identification string to explicitly allow concurrent instances on a public broker
        unique_client_id = f"tiot-group12-MQTTCatalogClient-{id}-{uuid.uuid4().hex[:6]}"
        
        self.client = mqtt.Client(client_id=unique_client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        self.pending_requests = {}
        self.lock = threading.Lock()

        self._connected_event = threading.Event()

    
    # SECTION 3: MQTT PROTOCOL CALLBACK CHANNELS
    def _on_connect(self, client, userdata, flags, rc):
        """
        Asynchronous hook triggered upon successful connection response from the broker.
        Subscribes to acknowledgement feeds and query response logs.
        """
        if rc == 0:
            print(f"\n[MQTT] Successfully connected to the Broker (Client: {self.ack_topic})")
            self.client.subscribe([(self.ack_topic, 2), (self.query_response_topic, 2)])
            self._connected_event.set()
        else:
            print(f"[MQTT] Connection failed. Error code: {rc}")

    def _on_message(self, client, userdata, msg):
        """
        Central processing node for inbound packets. Matches request IDs with pending tasks 
        and unlocks threads holding for reply parameters.
        """
        try:
            # Safely parse JSON text stream
            payload = json.loads(msg.payload.decode("utf-8"))
            request_id = payload.get("request_id")

            if not request_id:
                return

            with self.lock:
                if request_id in self.pending_requests:
                    # Estrazione sicura del payload tramite .get()
                    self.pending_requests[request_id]["response"] = payload.get("data", payload)
                    self.pending_requests[request_id]["event"].set()

        except Exception as e:
            print(f"[Message Decode Error]: {e}")
    # SECTION 4: ROUTING PIPELINE & DATA TRANSPORT LOGIC
    def _send_request(self, topic, payload, timeout=5):
        """
        Core pipeline method. Converts an asynchronous packet push into a blocking,
        thread-safe synchronous exchange using tracked UUIDs and signal timeout loops.
        """
        request_id = str(uuid.uuid4())
        payload["request_id"] = request_id
        event = threading.Event()
        with self.lock:
            self.pending_requests[request_id] = {"event": event, "response": None}

        self.client.publish(topic, json.dumps(payload))

        if not event.wait(timeout=timeout):
            with self.lock:
                del self.pending_requests[request_id]
            return None

        with self.lock:
            response = self.pending_requests[request_id]["response"]
            del self.pending_requests[request_id]

        return response
    # SECTION 5: INTERACTIVE DATABASE QUERY INTERFACES
    def get_catalog(self):
        """Fetches the comprehensive database contents from the central Catalog node."""
        payload = {
            "action": "get_all"
        }
        return self._send_request(self.query_request_topic, payload)
    
    def get_devices(self):
        """Retrieves all registered active devices within the Catalog framework."""
        payload = {
            "action": "get_devices"
        }
        return self._send_request(self.query_request_topic, payload)

    def get_services(self):
        """Retrieves all registered active services within the Catalog framework."""
        payload = {
            "action": "get_services"
        }
        return self._send_request(self.query_request_topic, payload)
    
    def get_device(self, id):
        """Retrieves an explicit individual device entry matching the specified object ID."""
        payload = {
            "action": "get_device_by_id",
            "id": id
        }
        return self._send_request(self.query_request_topic, payload)
    
    def get_service(self, id):
        """Retrieves an explicit individual service entry matching the specified object ID."""
        payload = {
            "action": "get_service_by_id",
            "id": id
        }
        return self._send_request(self.query_request_topic, payload)
    
    def get_broker(self):
        """Returns the in-memory fallback connection coordinates for the central system broker."""
        return {
            "ip": self.broker_ip,
            "port": self.broker_port
        }
    # SECTION 6: REGISTRATION & REFRESH ENDPOINTS
    def register_device(self, payload):
        """Performs initial database registration for an autonomous device entity."""
        payload = {
            "data": payload,
            "id": payload["id"],
            "category": "devices"
        }
        return self._send_request(self.register_topic, payload)

    def register_service(self, payload):
        """Performs initial database registration for a smart home service software actor."""
        payload = {
            "data": payload,
            "id": payload["id"],
            "category": "services"
        }
        return self._send_request(self.register_topic, payload)
    
    def refresh_device(self, id):
        """Sends a refresh signal to extend the lifespan of a registered device."""
        payload = {
            "category": "devices",
            "id": id
        }
        return self._send_request(self.register_topic, payload)

    def refresh_service(self, id):
        """Sends a refresh signal to extend the lifespan of a registered service."""
        payload = {
            "category": "services",
            "id": id
        }
        return self._send_request(self.register_topic, payload)
    # SECTION 7: LIFECYCLE MANAGEMENT ENDPOINTS
    def connect(self):
        """Establishes connection to the broker network and boots up background loop threads."""
        self.client.connect(self.broker_ip, self.broker_port)
        self.client.loop_start()
        if not self._connected_event.wait(timeout=10):
            raise TimeoutError("Could not connect to MQTT broker")
    
    def close(self):
        """Gracefully tears down subscriptions, cuts network linkages, and halts processing loops."""
        self.client.loop_stop()
        self.client.unsubscribe([self.ack_topic, self.query_response_topic])
        self.client.disconnect()
