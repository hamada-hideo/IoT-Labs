import paho.mqtt.client as mqtt
import json
import time
import threading
import os
import sys
from collections import deque

# Aggiungo il path per importare correttamente il CatalogClient
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from Catalog.catalog_client import CatalogClient

class SmartHomeController:
    def __init__(self):
        self.load_config()
        
        self.broker = "broker.emqx.io"
        self.port = 1883
        
        # Uso la wildcard per ascoltare tutta la casa (Sensori simulati + Arduino)
        self.global_sub_topic = "/tiot/group12/#"
        self.base_command_topic = "/tiot/group12/actuators/commands" # Topic legacy per Arduino
        
        self.client_id = f"Controller_Group12_{int(time.time())}"

        self.temp_window = deque(maxlen=self.config["rolling_window_size"])

        self.room_state = {
            "lights": False,
            "fan": 0,
            "lcd": "",
            "green_lights": False
        }
        self.last_presence_time = 0
        self.is_running = True

        # --- INTEGRAZIONE CATALOG CLIENT ---
        self.cc = CatalogClient()
        self.registered = False
        self.service_payload = {
            "id": "smart_home_controller",
            "description": "Rule Engine Python con statistiche e gestione presenza",
            "endpoints": [self.global_sub_topic]
        }

        # --- CONFIGURAZIONE MQTT V1 (Senza CallbackAPIVersion) ---
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                self.config = json.load(f)
            print("[CONFIG] Impostazioni caricate correttamente da config.json")
        except Exception as e:
            print(f"[CONFIG] Errore caricamento file. Uso valori di fallback. {e}")
            self.config = {
                "temperature_threshold": 26.0,
                "presence_timeout_seconds": 60,
                "rolling_window_size": 10
            }

    def register_and_keep_alive(self):
        """Usa il CatalogClient ufficiale per mantenere viva la registrazione"""
        while self.is_running:
            try:
                if not self.registered:
                    if self.cc.register_service(self.service_payload):
                        self.registered = True
                        print(f"[REST] Controller registrato al Catalogo con successo.")
                else:
                    if not self.cc.refresh_service(self.service_payload["id"]):
                        self.registered = False
                        print(f"[REST] Fallito il refresh al Catalogo.")
            except Exception as e:
                print(f"[REST KEEP-ALIVE] Errore di comunicazione col Catalogo: {e}")
            
            time.sleep(self.cc.loop_time)

    # --- MQTT V1: Usa 'rc', niente properties ---
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] Connesso al broker")
            self.client.subscribe(self.global_sub_topic)
            print(f"[MQTT] Iscritto al topic globale: {self.global_sub_topic}")
        else:
            print(f"[MQTT] Errore di connessione, codice: {rc}")

    def send_command(self, actuator, value, unit):
        """Invia comando. Attualmente punta all'Arduino (blind command)"""
        if self.room_state.get(actuator) == value:
            return 

        self.room_state[actuator] = value
        payload = {
            "bn": "smart_home/living_room/",
            "e": [{"n": actuator, "v": value, "u": unit, "t": time.time()}]
        }
        self.client.publish(self.base_command_topic, json.dumps(payload))
        print(f"> [COMANDO ARDUINO] living_room -> {actuator}: {value}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            
            # Estrazione degli eventi SenML (se presenti, altrimenti lista vuota)
            events = payload.get("e", [])
            if not events:
                return # Ignora messaggi non SenML (o ACK del catalogo)

            for event in events:
                if event.get("n") == "system":
                    return

            current_temp = None
            pir_motion = False

            for event in events:
                name = event.get("n")
                val = event.get("v")

                # Intercetta sia la temperatura di Arduino che quella simulata
                if "temperature" in name or name == "temperature":
                    current_temp = val
                elif name == "motion" and val is True:
                    pir_motion = True
                    self.last_presence_time = time.time()
                elif name == "noise_event" and val is True:
                    print("\n⚡ [EVENTO EDGE] Rilevato doppio applauso dall'Arduino!")
                    self.last_presence_time = time.time()
                    new_green_state = not self.room_state["green_lights"]
                    self.send_command("green_lights", new_green_state, "bool")

            time_since_last_presence = time.time() - self.last_presence_time
            is_room_occupied = time_since_last_presence < self.config["presence_timeout_seconds"]

            if current_temp is not None:
                self.temp_window.append(current_temp)
                
                t_mean = sum(self.temp_window) / len(self.temp_window)
                print(f"[STATS] Media Mobile Temp: {t_mean:.1f}°C (da {msg.topic})")

                lcd_text = f"T:{t_mean:.1f}C"

                if t_mean > self.config["temperature_threshold"]:
                    self.send_command("lights", False, "bool")
                    self.send_command("fan", 100, "percent")
                    lcd_text += " AC:100%"
                elif is_room_occupied:
                    self.send_command("lights", True, "bool")
                    self.send_command("fan", 0, "percent")
                    lcd_text += " AC:0%"
                else:
                    self.send_command("lights", False, "bool")
                    self.send_command("fan", 0, "percent")
                    lcd_text += " Vuota"

                self.send_command("lcd", lcd_text, "string")

        except json.JSONDecodeError:
            pass # Ignora traffico non JSON sniffato dalla wildcard
        except Exception as e:
            print(f"[ERRORE] Elaborazione messaggio: {e}")

    def start(self):
        self.keep_alive_thread = threading.Thread(target=self.register_and_keep_alive)
        self.keep_alive_thread.daemon = True
        self.keep_alive_thread.start()

        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[SISTEMA] Arresto in corso...")
            self.is_running = False
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    controller = SmartHomeController()
    controller.start()
