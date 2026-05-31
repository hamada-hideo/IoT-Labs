import sys
import os
import json
import time
import paho.mqtt.client as mqtt

# Importiamo la classe Catalog dal vostro file catalog_service.py
from catalog_service import Catalog

class MQTTCatalogBridge:
    def __init__(self, catalog_instance):
        # Salviamo il riferimento al catalogo comune passato come parametro
        self.catalog_service = catalog_instance

        # Inizializziamo il client MQTT
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Scegliamo un topic globale per le registrazioni (definito dal vostro team)
        self.registration_topic = "/tiot/group12/catalog/register"
        self.query_request_topic = "/tiot/group12/catalog/query/request"
        self.query_response_topic = "/tiot/group12/catalog/query/response"

        self.broker_ip = self.catalog_service.catalog["broker"]["ip"]
        self.broker_port = self.catalog_service.catalog["broker"]["port"]
        try:
            self.client.connect(self.broker_ip, self.broker_port, 60)
        except:
            print(f"[MQTT] Impossibile connettersi al broker su {self.broker_ip}:{self.broker_port}")
        self.running = True

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.client.subscribe(self.query_request_topic)
            print(f"[MQTT] Connesso con successo al Broker su {self.broker_ip}:{self.broker_port}!")
            # Appena si connette, si iscrive al canale dove i dispositivi mandano i dati
            self.client.subscribe(self.registration_topic)
            print(f"[MQTT] Iscritto al topic di registrazione: {self.registration_topic}")
        else:
            print(f"[MQTT] Errore di connessione. Codice: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            # 1. Decodifichiamo il payload JSON ricevuto
            payload = json.loads(msg.payload.decode("utf-8"))
            print(f"\n[MQTT] Ricevuto messaggio su {msg.topic}: {payload}")

            # --- SPOSTATO QUI ALL'INIZIO ---
            # Se il messaggio arriva sul topic delle query, lo gestiamo subito ed esciamo
            if msg.topic == self.query_request_topic:
                self._handle_query(payload)
            elif msg.topic == self.registration_topic:
                self._handle_registration(payload)
        except json.JSONDecodeError:
            print("[MQTT] Errore: Il messaggio ricevuto non è in un formato JSON valido.")
        except Exception as e:
            print(f"[MQTT] Errore durante l'elaborazione del messaggio: {e}")

    def run(self):
        self.client.loop_start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
            self.running = False
            self.client.loop_stop()
            self.client.unsubscribe([self.registration_topic, self.query_request_topic])
            self.client.disconnect()
            print("Disconnected")

    def _handle_query(self, payload):
        action = payload.get("action")
        with self.catalog_service.lock:
            if action == "get_all":
                result = self.catalog_service.catalog
            elif action == "get_devices":
                result = self.catalog_service.catalog["devices"]
            elif action == "get_services":
                result = self.catalog_service.catalog["services"]
            elif action == "get_device_by_id":
                device_id = payload.get("id")
                result = self.catalog_service.catalog["devices"].get(device_id, {"error": "not found"})
            elif action == "get_service_by_id":
                service_id = payload.get("id")
                result = self.catalog_service.catalog["services"].get(service_id, {"error": "not found"})
            else:
                result = {"error": "unknown action"}
        self.client.publish(self.query_response_topic, json.dumps(result))
        print(f"[MQTT] Query response inviata su {self.query_response_topic}")

    def _handle_registration(self, payload):
        # 2. VALIDAZIONI PER LA REGISTRAZIONE / REFRESH DEI DISPOSITIVI
        category = payload.get("category", "devices")
        if category not in ["devices", "services"]:
            print("[MQTT] Errore: Categoria non valida. Usa 'devices' o 'services'")
            return

        item_id = payload.get("id")
        if not item_id:
            print("[MQTT] Errore: Il payload non contiene un 'id'")
            return

        # 3. STRUTTURA DEL REFRESH O INSERIMENTO (Usando il LOCK del catalogo)
        with self.catalog_service.lock:
            if item_id in self.catalog_service.catalog[category]:
                payload['insert_timestamp'] = time.time()
                self.catalog_service.catalog[category][item_id] = payload
                print(f"[MQTT] Refresh effettuato per {item_id}")
            else:
                payload['insert_timestamp'] = time.time()
                self.catalog_service.catalog[category][item_id] = payload
                print(f"[MQTT] Nuovo {category[:-1]} registrato con successo via MQTT")

            self.catalog_service._save_catalog()

        # 4. PUBBLICAZIONE DELL'ACKNOWLEDGEMENT (ACK)
        response_topic = f"/tiot/group12/catalog/ack/{item_id}"
        ack_message = {
            "status": "success",
            "message": f"Registrazione/Refresh di {item_id} elaborata dal Catalogo."
        }
        self.client.publish(response_topic, json.dumps(ack_message))
        print(f"[MQTT] ACK inviato sul topic: {response_topic}")

# Questo va in fondo al file mqtt_catalog_bridge.py, al posto del vecchio blocco 'if __name__ == "__main__":'
def start_mqtt_bridge(catalog_instance):
    # Passiamo l'istanza del catalogo già creata dal main
    bridge = MQTTCatalogBridge(catalog_instance)
    bridge.run()
