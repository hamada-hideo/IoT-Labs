import paho.mqtt.client as mqtt
import requests
import json
import time
import threading
import os
from collections import deque

class SmartHomeController:
    def __init__(self):
        self.load_config()
        
        self.broker = "broker.emqx.io"
        self.port = 1883
        self.base_topic = "/tiot/group12"
        self.client_id = f"Controller_Group12_{int(time.time())}"

        # Strutture dati per le statistiche mobili
        self.temp_window = deque(maxlen=self.config["rolling_window_size"])

        # Stato della Presenza e del Sistema
        self.room_state = {
            "lights": False,
            "fan": 0,
            "lcd": "",
            "green_lights": False
        }
        self.last_presence_time = 0  # Timestamp dell'ultima rilevazione (PIR o Audio)
        self.is_running = True

        # Configurazione Client MQTT
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def load_config(self):
        """Carica le soglie dal file JSON esterno"""
        try:
            with open("config.json", "r") as f:
                self.config = json.load(f)
            print("[CONFIG] Impostazioni caricate correttamente da config.json")
        except Exception as e:
            print(f"[CONFIG] Errore caricamento file. Uso valori di fallback. {e}")
            self.config = {
                "catalog_url": "http://127.0.0.1:8080",
                "temperature_threshold": 26.0,
                "presence_timeout_seconds": 60,
                "rolling_window_size": 10
            }

    def register_and_keep_alive(self):
        """Invia la registrazione iniziale e mantiene il Keep-Alive attivo via REST (Ex 13.1)"""
        service_info = {
            "service_id": "smart_home_controller",
            "description": "Rule Engine Python con statistiche e gestione presenza",
            "endpoints": [self.base_topic]
        }
        url = f"{self.config['catalog_url']}/catalog/services"
        
        while self.is_running:
            try:
                # Usiamo POST o PUT a seconda delle specifiche del tuo Catalog per l'update
                res = requests.post(url, json=service_info, timeout=5)
                if res.status_code in [200, 201]:
                    print(f"[REST KEEP-ALIVE] Registrazione aggiornata al Catalogo. Stato: {res.status_code}")
                else:
                    print(f"[REST KEEP-ALIVE] Errore Catalogo: {res.status_code}")
            except Exception as e:
                print(f"[REST KEEP-ALIVE] Catalogo non raggiungibile: {e}")
            
            # Attende 30 secondi prima del prossimo battito di keep-alive
            time.sleep(30)

    def on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connesso al broker {self.broker}")
        sub_topic = f"{self.base_topic}/sensors/telemetry"
        self.client.subscribe(sub_topic)
        print(f"[MQTT] Iscritto al topic di telemetria: {sub_topic}")

    def send_command(self, actuator, value, unit):
        """Invia comandi SenML filtrando i duplicati (Anti-Spam)"""
        if self.room_state.get(actuator) == value:
            return 

        self.room_state[actuator] = value
        topic = f"{self.base_topic}/actuators/commands"
        payload = {
            "bn": "smart_home/living_room/",
            "e": [{"n": actuator, "v": value, "u": unit, "t": time.time()}]
        }
        self.client.publish(topic, json.dumps(payload))
        print(f"> [COMANDO] living_room -> {actuator}: {value}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            events = payload.get("e", [])
            
            # Controllo preliminare per i comandi di sistema 
            for event in events:
                if event.get("n") == "system":
                    return # Se è un comando di switch interno, non lo processiamo come telemetria

            current_temp = None
            pir_motion = False

            # --- PARSING EVENTI SENML ---
            for event in events:
                name = event.get("n")
                val = event.get("v")

                if name == "temperature":
                    current_temp = val
                elif name == "motion" and val is True:
                    pir_motion = True
                    self.last_presence_time = time.time() # Reset del timer presenza via Hardware
                elif name == "noise_event" and val is True:
                    print("\n⚡ [EVENTO EDGE] Rilevato doppio applauso dall'Arduino!")
                    self.last_presence_time = time.time() # Reset del timer presenza via Audio
                    # Inversione dello stato della luce verde controllata da Python
                    new_green_state = not self.room_state["green_lights"]
                    self.send_command("green_lights", new_green_state, "bool")

            # --- MACCHINA A STATI DELLA PRESENZA ---
            time_since_last_presence = time.time() - self.last_presence_time
            is_room_occupied = time_since_last_presence < self.config["presence_timeout_seconds"]

            # --- CALCOLO STATISTICHE MOBILI ---
            if current_temp is not None:
                self.temp_window.append(current_temp)
                
                t_min = min(self.temp_window)
                t_max = max(self.temp_window)
                t_mean = sum(self.temp_window) / len(self.temp_window)
                
                print(f"\n[STATS] Ultime {len(self.temp_window)} letture -> Min: {t_min:.1f}°C | Max: {t_max:.1f}°C | Media: {t_mean:.1f}°C")

                # Verifica superamento soglia critica sulla MEDIA
                if t_mean > self.config["temperature_threshold"]:
                    alert_topic = f"{self.base_topic}/alerts"
                    alert_payload = {
                        "alert": "TEMPERATURE_EXCEEDED",
                        "current_mean": round(t_mean, 2),
                        "threshold": self.config["temperature_threshold"],
                        "timestamp": time.time()
                    }
                    self.client.publish(alert_topic, json.dumps(alert_payload))
                    print(f"🚨 [ALLARME MQTT] Pubblicato su {alert_topic}: Media critica {t_mean:.1f}°C!")

                # --- REGOLE (Rule Engine su base Media e Presenza) ---
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
                    # Nessuna presenza -> Tutto spento
                    self.send_command("lights", False, "bool")
                    self.send_command("fan", 0, "percent")
                    lcd_text += " Vuota"

                # Invia la stringa LCD già formattata da Python
                self.send_command("lcd", lcd_text, "string")

        except Exception as e:
            print(f"[ERRORE] Errore nel processamento del messaggio: {e}")

    def start(self):
        # Avvio del thread separato per il Keep-Alive REST
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
