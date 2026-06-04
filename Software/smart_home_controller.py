import paho.mqtt.client as mqtt
import time
import json
import threading
import os
from collections import deque

# Il client REST per la registrazione
from Catalog.catalog_client import CatalogClient 

DIR = os.path.dirname(os.path.abspath(__file__))

class SmartHomeController:
    def __init__(self, device_id):
        self.device_id = device_id
        
        self.catalog = CatalogClient()
        
        config_file = os.path.join(DIR, "network_config.json")
        with open(config_file, "r") as f:
            network_data = json.load(f)
        self.broker_ip = network_data["mqtt"]["broker"]["ip"]
        self.broker_port = network_data["mqtt"]["broker"]["port"]

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"Controller_{self.device_id}_{int(time.time())}")
        self.client.on_message = self.on_message

        # Topic allineati
        self.topic_telemetry = "/tiot/group12/sensors/telemetry"
        self.topic_commands = "/tiot/group12/actuators/commands"
        self.topic_alerts = "/tiot/group12/alerts"

        # Dizionario delle stanze
        self.rooms = {} 

        self.temp_threshold = 26.0
        self.alert_threshold = 30.0
        
        self.registered = False
        self.data = {} 

    def _try_register_refresh_loop(self):
        while True:
            time.sleep(self.catalog.loop_time)
            if not self.registered:
                if self.catalog.register_service(self.data):
                    self.registered = True
                    print(f"[Controller] Registrato con successo al Catalogo via REST.")
            else:
                if not self.catalog.refresh_service(self.device_id):
                    self.registered = False
                    print(f"[Controller] Errore nel refresh, ritento la registrazione...")

    def setup(self):
        self.data = {
            "id": self.device_id,
            "description": "Integrated Smart Home Controller (Ex 13 & 14)",
            "mqtt": {
                "sub_topics": [self.topic_telemetry], 
                "pub_topics": [self.topic_commands, self.topic_alerts]
            },
            "resources": ["controller"]
        }
        threading.Thread(target=self._try_register_refresh_loop, daemon=True).start()

    def start(self):
        self.setup()
        self.client.connect(self.broker_ip, self.broker_port, 60)
        self.client.subscribe(self.topic_telemetry) 
        print(f"[{self.device_id}] Avviato e in ascolto su MQTT...")
        self.client.loop_forever()

    def _get_room_data(self, room_name):
        if room_name not in self.rooms:
            self.rooms[room_name] = {
                "motion": False,
                "noise": 0.0, 
                "temp_history": deque(maxlen=10),
                "led_state": None,
                "fan_speed": None,
                "lcd_text": "" 
            }
        return self.rooms[room_name]

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            events = payload.get("e", [])
            base_name = payload.get("bn", "") 
            
            for event in events:
                full_name = base_name + event["n"]
                segments = full_name.strip('/').split('/')
                
                if len(segments) >= 2:
                    room_name = segments[-2] 
                    sensor_type = segments[-1]
                    
                    if "temperature" in sensor_type:
                        self.handle_temperature(room_name, event["v"])
                    elif "motion" in sensor_type:
                        room_data = self._get_room_data(room_name)
                        room_data["motion"] = bool(event["v"])
                        self.evaluate_rules(room_name)
                    elif "noise" in sensor_type:
                        # Ricezione sensore di rumore dall'Arduino
                        room_data = self._get_room_data(room_name)
                        room_data["noise"] = float(event["v"])
                        # Il rumore potrebbe triggerare altre logiche in futuro!
        except Exception:
            pass

    def handle_temperature(self, room_name, temp):
        room_data = self._get_room_data(room_name)
        room_data["temp_history"].append(temp)
        
        if len(room_data["temp_history"]) == 10:
            min_t = min(room_data["temp_history"])
            max_t = max(room_data["temp_history"])
            mean_t = sum(room_data["temp_history"]) / 10
            
            if mean_t > self.alert_threshold:
                alert_msg = {
                    "bn": f"smart_home/{room_name}/", 
                    "e": [{"n": "alert", "t": time.time(), "v": "Temperatura media critica!", "u": "String"}]
                }
                self.client.publish(self.topic_alerts, json.dumps(alert_msg))
                print(f">> [ALLARME] Temperatura critica in {room_name}! <<")

        self.evaluate_rules(room_name)
        self.update_actuators_and_lcd(room_name, temp)

    def evaluate_rules(self, room_name):
        room_data = self._get_room_data(room_name)
        if not room_data["temp_history"]: return
        current_temp = room_data["temp_history"][-1]

        if not room_data["motion"]:
            self.send_led_command(room_name, False)
        else:
            if current_temp > self.temp_threshold:
                self.send_led_command(room_name, False)
            elif current_temp < self.temp_threshold:
                self.send_led_command(room_name, True)

    def send_led_command(self, room_name, state):
        room_data = self._get_room_data(room_name)
        
        if room_data["led_state"] != state:
            cmd = {
                "bn": "smart_home/", 
                "e": [{"n": f"{room_name}/lights", "t": time.time(), "v": state, "u": "bool"}]
            }
            self.client.publish(self.topic_commands, json.dumps(cmd))
            room_data["led_state"] = state
            print(f"[COMANDO] {room_name}: Luci {'ACCESE' if state else 'SPENTE'}")

    def update_actuators_and_lcd(self, room_name, current_temp):
        ac_min_setpoint = 25.0
        ac_max_setpoint = 30.0
        
        if current_temp <= ac_min_setpoint:
            ac_speed = 0
        elif current_temp >= ac_max_setpoint:
            ac_speed = 100
        else:
            ac_speed = int(((current_temp - ac_min_setpoint) / (ac_max_setpoint - ac_min_setpoint)) * 100)
            
        room_data = self._get_room_data(room_name)
        
        # Ottimizzazione e Invio comando Fan
        if room_data["fan_speed"] != ac_speed:
            fan_cmd = {
                "bn": "smart_home/",
                "e": [{"n": f"{room_name}/fan", "t": time.time(), "v": ac_speed, "u": "%"}]
            }
            self.client.publish(self.topic_commands, json.dumps(fan_cmd))
            room_data["fan_speed"] = ac_speed
            print(f"[COMANDO] {room_name}: Ventola al {ac_speed}%")

        # Creiamo una stringa formattata da far leggere all'utente sullo schermino
        new_lcd_text = f"T:{current_temp:.1f}C AC:{ac_speed}%"
        
        # Invia il messaggio MQTT solo se il testo sul display deve cambiare
        if room_data["lcd_text"] != new_lcd_text:
            lcd_cmd = {
                "bn": "smart_home/",
                "e": [{"n": f"{room_name}/lcd", "t": time.time(), "v": new_lcd_text, "u": "String"}]
            }
            self.client.publish(self.topic_commands, json.dumps(lcd_cmd))
            room_data["lcd_text"] = new_lcd_text
            print(f"[COMANDO] {room_name}: Aggiornato display LCD -> '{new_lcd_text}'")

if __name__ == '__main__':
    controller = SmartHomeController("Controller_Group12")
    controller.start()