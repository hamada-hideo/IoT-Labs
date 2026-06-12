import paho.mqtt.client as mqtt
import json
import time
import threading
import os
import sys
from collections import deque

# Assicura che Python trovi i moduli del team (Catalog e SenMLUtils)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from Catalog.catalog_client import CatalogClient
import SenMLUtils as SenML

DIR = os.path.dirname(os.path.abspath(__file__))

class SmartHomeController:
    def __init__(self):
        # Configurazione dinamica: nessun dato di rete o soglia hardcodata
        self.config_file = os.path.join(DIR, "controller_config.json")
        with open(self.config_file, "r") as f:
            self.config = json.load(f)
            
        self.sub_topic = self.config["mqtt"]["global_sub_topic"]
        self.alert_topic = self.config["mqtt"]["alert_topic"]
        self.threshold = self.config["temperature_threshold"]
        
        self.client_id = f"Controller_Group12_{int(time.time())}"

        # Gestione Multi-Stanza: Dizionari separati per ogni ambiente
        self.temp_windows = {}
        self.presence_timers = {}
        
        # Device Shadow: Copia locale dell'ultimo stato noto degli attuatori
        self.room_shadow_state = {}

        self.cc = CatalogClient()
        self.registered = False
        self.service_payload = {
            "id": "smart_home_controller",
            "description": "Rule Engine Centralizzato Multi-Stanza",
            "endpoints": [self.sub_topic]
        }
        
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.is_running = True

    def _get_broker_loop(self):
        """Interroga il Catalog REST per farsi dare IP e Porta del Broker"""
        while self.is_running:
            broker = self.cc.get_broker()
            if broker:
                self.broker_host = broker["ip"]
                self.broker_port = broker["port"]
                break
            time.sleep(self.cc.loop_time)

    def register_and_keep_alive(self):
        """Mantiene viva la registrazione del Controller sul Catalog REST"""
        while self.is_running:
            try:
                if not self.registered:
                    if self.cc.register_service(self.service_payload):
                        self.registered = True
                        print("[REST] Registrazione al Catalogo completata.")
                else:
                    if not self.cc.refresh_service(self.service_payload["id"]):
                        self.registered = False
            except Exception:
                pass
            time.sleep(self.cc.loop_time)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] Connesso al broker. Iscritto a: {self.sub_topic}")
            self.client.subscribe(self.sub_topic)

    def send_command(self, room, actuator, value, unit):
        """Costruisce e invia un comando MQTT formattato in SenML"""
        if room not in self.room_shadow_state:
            self.room_shadow_state[room] = {}
        
        # Anti-spam: se l'attuatore è già in quello stato, non inviare il comando
        if self.room_shadow_state[room].get(actuator) == value:
            return
            
        self.room_shadow_state[room][actuator] = value

        # Utilizzo della libreria di team SenMLUtils
        base_name = f"smart_home/{room}/"
        event = SenML.build_event_dict(actuator, unit, value, time.time())
        payload = SenML.build_array_dict([event], basename=base_name)

        # Routing: seleziona il topic corretto in base all'hardware/simulatore
        if room == "living_room":
            topic = self.config["mqtt"]["arduino_command_topic"]
        else:
            topic = self.config["mqtt"]["simulated_command_topic_template"].format(room=room, id=actuator)

        self.client.publish(topic, json.dumps(payload))
        print(f"> [COMANDO] {room} -> {actuator}: {value}")

    def on_message(self, client, userdata, msg):
        # Ignora i messaggi provenienti dal vecchio publisher (formato non-SenML)
        if "temperature/config" in msg.topic or msg.topic == "/tiot/group12/temperature":
            return

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if not SenML.validate_SenML(payload):
                return
            
            flat_events = SenML.flatten_senml(payload)
            rooms_to_process = set()

            # Estrazione Dati e aggiornamento finestre mobili per singola stanza
            for event in flat_events:
                name_parts = event["n"].split("/")
                if len(name_parts) >= 3 and name_parts[0] == "smart_home":
                    room = name_parts[1]
                    sensor = name_parts[2]
                    val = event["v"]
                    rooms_to_process.add(room)

                    if sensor == "temperature":
                        if room not in self.temp_windows:
                            self.temp_windows[room] = deque(maxlen=self.config["rolling_window_size"])
                        self.temp_windows[room].append(val)
                    
                    elif sensor == "motion" and val is True:
                        self.presence_timers[room] = time.time()
                        
                    elif sensor == "noise_event" and val is True:
                        self.presence_timers[room] = time.time()
                        # Toggle della luce verde esclusivo per l'Arduino (living_room)
                        if room == "living_room":
                            current_green = self.room_shadow_state.get(room, {}).get("green_lights", False)
                            self.send_command(room, "green_lights", not current_green, "bool")

            # Valutazione del Rule Engine per le stanze che hanno ricevuto nuovi dati
            for room in rooms_to_process:
                last_presence = self.presence_timers.get(room, 0)
                is_occupied = (time.time() - last_presence) < self.config["presence_timeout_seconds"]

                if room in self.temp_windows and len(self.temp_windows[room]) > 0:
                    t_mean = sum(self.temp_windows[room]) / len(self.temp_windows[room])
                    
                    # LOGICA 1: Temperatura oltre la soglia
                    if t_mean > self.threshold:
                        self.send_command(room, "lights", False, "bool")
                        self.send_command(room, "fan", 100, "percent")
                        if room == "living_room":
                            self.send_command(room, "lcd", f"T:{t_mean:.1f}C AC:100%", "string")
                            
                        # Allarme MQTT sul topic dedicato
                        alert_payload = {"room": room, "alert": "TEMP_CRITICAL", "mean": round(t_mean, 2)}
                        self.client.publish(self.alert_topic, json.dumps(alert_payload))
                        print(f"🚨 [ALERT] Temp critica in {room}: {t_mean:.1f}°C")
                        
                    # LOGICA 2: Temperatura sotto controllo, ma stanza occupata
                    elif is_occupied:
                        self.send_command(room, "lights", True, "bool")
                        self.send_command(room, "fan", 0, "percent")
                        if room == "living_room":
                            self.send_command(room, "lcd", f"T:{t_mean:.1f}C AC:0%", "string")
                            
                    # LOGICA 3: Stanza vuota e temperatura sotto controllo
                    else:
                        self.send_command(room, "lights", False, "bool")
                        self.send_command(room, "fan", 0, "percent")
                        if room == "living_room":
                            self.send_command(room, "lcd", f"T:{t_mean:.1f}C Vuota", "string")

        except json.JSONDecodeError:
            pass # Ignora payload malformati sniffati sulla rete

    def start(self):
        # Avvio della sequenza di connessione e keep-alive
        self._get_broker_loop()
        threading.Thread(target=self.register_and_keep_alive, daemon=True).start()
        
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nArresto in corso...")
            self.is_running = False
            self.client.disconnect()

if __name__ == "__main__":
    controller = SmartHomeController()
    controller.start()
