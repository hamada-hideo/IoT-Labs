import json
import os
import time
import paho.mqtt.client as mqtt
import threading
import uuid

DIR = os.path.dirname(os.path.abspath(__file__))

class MQTTCatalogClient:
    
    def __init__(self, id):
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.broker_ip = data["mqtt"]["broker"]["ip"]
        self.broker_port = data["mqtt"]["broker"]["port"]
        self.register_topic = data["mqtt"]["register_topic"]
        self.ack_topic = data["mqtt"]["ack_topic"].replace("<id>", id)
        self.query_request_topic = data["mqtt"]["query_request_topic"]
        self.query_response_topic = data["mqtt"]["query_response_topic"]
        self.loop_time = data["expiration_time"] // 2

        self.client = mqtt.Client(client_id=f"tiot-group12-MQTTCatalogClient-{id}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        self.pending_requests = {}
        self.lock = threading.Lock()

        self._connected_event = threading.Event()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("\n[MQTT] Successfully connected to the Broker!")
            self.client.subscribe([(self.ack_topic, 2), (self.query_response_topic, 2)])
            self._connected_event.set()
        else:
            print(f"[MQTT] Connection failed. Error code: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            request_id = payload.get("request_id")

            if not request_id:
                return

            with self.lock:
                if request_id in self.pending_requests:
                    self.pending_requests[request_id]["response"] = payload["data"]
                    self.pending_requests[request_id]["event"].set()

        except Exception as e:
            print(f"[Message Decode Error]: {e}")

    def _send_request(self, topic, payload, timeout=5):
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

    def get_catalog(self):
        payload = {
            "action": "get_all"
        }
        return self._send_request(self.query_request_topic, payload)
    
    def get_devices(self):
        payload = {
            "action": "get_devices"
        }
        return self._send_request(self.query_request_topic, payload)

    
    def get_services(self):
        payload = {
            "action": "get_services"
        }
        return self._send_request(self.query_request_topic, payload)
    
    def get_device(self, id):
        payload = {
            "action": "get_device_by_id",
            "id": id
        }
        return self._send_request(self.query_request_topic, payload)
    
    def get_service(self, id):
        payload = {
            "action": "get_service_by_id",
            "id": id
        }
        return self._send_request(self.query_request_topic, payload)
    
    def get_broker(self):
        return {
            "ip": self.broker_ip,
            "port": self.broker_port
        }
    
    def register_device(self, payload):
        payload = {
            "data": payload,
            "id": payload["id"],
            "category": "devices"
        }
        return self._send_request(self.register_topic, payload)

    def register_service(self, payload):
        payload = {
            "data": payload,
            "id": payload["id"],
            "category": "services"
        }
        return self._send_request(self.register_topic, payload)
    
    def refresh_device(self, id):
        payload = {
            "category": "devices",
            "id": id
        }
        return self._send_request(self.register_topic, payload)

    def refresh_service(self, id):
        payload = {
            "category": "services",
            "id": id
        }
        return self._send_request(self.register_topic, payload)

    def connect(self):
        self.client.connect(self.broker_ip, self.broker_port)
        self.client.loop_start()
        if not self._connected_event.wait(timeout=10):
            raise TimeoutError("Could not connect to MQTT broker")
    
    def close(self):
        self.client.loop_stop()
        self.client.unsubscribe([self.ack_topic, self.query_response_topic])
        self.client.disconnect()
