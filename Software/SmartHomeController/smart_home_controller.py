import paho.mqtt.client as mqtt
import json
import time
import threading
import os
import sys
from collections import deque

# --- FIX PATH: Doppio salto indietro garantito ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
GRANDPARENT_DIR = os.path.dirname(PARENT_DIR)

if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
if GRANDPARENT_DIR not in sys.path:
    sys.path.insert(0, GRANDPARENT_DIR)

from Catalog.catalog_client import CatalogClient
import SenMLUtils as SenML

class SmartHomeController:
    def __init__(self):
        self.config_file = os.path.join(CURRENT_DIR, "controller_config.json")
        with open(self.config_file, "r") as f:
            self.config = json.load(f)
            
        self.sub_topic = self.config["mqtt"]["global_sub_topic"]
        self.alert_topic = self.config["mqtt"]["alert_topic"]
        self.target_temp = self.config["target_temperature"]
        self.critical_temp = self.config["critical_temperature"]
        
        self.client_id = f"Controller_Group12_{int(time.time())}"

        self.temp_windows = {}
        self.presence_timers = {}
        self.room_shadow_state = {}
        self.home_topology = {}

        self.cc = CatalogClient()
        self.registered = False
        self.service_payload = {
            "id": "smart_home_controller",
            "description": "Rule Engine Scalabile Agnostico e Stateless",
            "endpoints": [self.sub_topic]
        }
        
        # FIX DEPRECATION WARNING: Aggiunto esplicitamente VERSION1
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.is_running = True

    def _get_broker_loop(self):
        while self.is_running:
            broker = self.cc.get_broker()
            if broker:
                self.broker_host = broker["ip"]
                self.broker_port = broker["port"]
                break
            time.sleep(self.cc.loop_time)

    def _sync_topology(self):
        while self.is_running:
            try:
                devices = self.cc.get_devices()
                if devices and "error" not in devices:
                    new_topology = {}
                    for dev_id, dev_info in devices.items():
                        parts = dev_id.split("/")
                        if len(parts) >= 2:
                            room = parts[0]
                            dev_name = parts[1]
                            
                            if room not in new_topology:
                                new_topology[room] = {"sensors": {}, "actuators": {}}
                            
                            res_type = dev_info.get("resources", {}).get("type", dev_name)
                            
                            if "mqtt" in dev_info and "command_topic" in dev_info["mqtt"]:
                                new_topology[room]["actuators"][dev_name] = {
                                    "type": res_type,
                                    "unit": dev_info.get("resources", {}).get("unit", ""),
                                    "command_topic": dev_info["mqtt"]["command_topic"]
                                }
                            else:
                                new_topology[room]["sensors"][dev_name] = {"type": res_type}
                    self.home_topology = new_topology
            except Exception:
                pass
            time.sleep(self.cc.loop_time)

    def register_and_keep_alive(self):
        while self.is_running:
            try:
                if not self.registered:
                    if self.cc.register_service(self.service_payload):
                        self.registered = True
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

    def send_command(self, room, actuator_id, actuator_info, value):
        base_name = f"smart_home/{room}/"
        event = SenML.build_event_dict(actuator_id, actuator_info["unit"], value, time.time())
        payload = SenML.build_array_dict([event], basename=base_name)
        topic = actuator_info["command_topic"]
        self.client.publish(topic, json.dumps(payload))
        print(f"> [COMANDO EMESSO] {room}/{actuator_id} ({actuator_info['type']}) -> {value}")

    def _dispatch_by_type(self, room, target_type, value):
        room_actuators = self.home_topology.get(room, {}).get("actuators", {})
        for act_id, act_info in room_actuators.items():
            if act_info["type"] == target_type:
                self.send_command(room, act_id, act_info, value)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if not SenML.validate_SenML(payload):
                return
            
            flat_events = SenML.flatten_senml(payload)
            rooms_to_process = set()

            for event in flat_events:
                name_parts = event["n"].split("/")
                if len(name_parts) >= 3 and name_parts[0] == "smart_home":
                    room = name_parts[1]
                    sensor_id = name_parts[2]
                    val = event["v"]
                    
                    sensor_info = self.home_topology.get(room, {}).get("sensors", {}).get(sensor_id, {})
                    if not sensor_info:
                        sensor_info = self.home_topology.get(room, {}).get("actuators", {}).get(sensor_id, {})
                    sensor_type = sensor_info.get("type", sensor_id)

                    if sensor_type == "temperature":
                        rooms_to_process.add(room)
                        if room not in self.temp_windows:
                            self.temp_windows[room] = deque(maxlen=self.config["rolling_window_size"])
                        self.temp_windows[room].append(val)
                    
                    elif sensor_type == "motion" and val is True:
                        rooms_to_process.add(room)
                        self.presence_timers[room] = time.time()
                        
                    elif sensor_type == "noise_event" and val is True:
                        self.presence_timers[room] = time.time()
                        room_acts = self.home_topology.get(room, {}).get("actuators", {})
                        for act_id, act_info in room_acts.items():
                            if act_info["type"] == "green_lights":
                                current_real_state = self.room_shadow_state.get(room, {}).get(act_id, False)
                                self.send_command(room, act_id, act_info, not current_real_state)
                    
                    # --- FIX HEATER INCLUSO NEL FEEDBACK HARDWARE ---
                    elif sensor_type in ["fan", "heater", "lights", "green_lights", "blinds", "lcd"]:
                        if room not in self.room_shadow_state:
                            self.room_shadow_state[room] = {}
                        self.room_shadow_state[room][sensor_id] = val

            # --- MOTORE DI VALUTAZIONE REGOLE INDUSTRIALE (ECO SET-POINTS) ---
            for room in rooms_to_process:
                last_presence = self.presence_timers.get(room, 0)
                is_occupied = (time.time() - last_presence) < self.config["presence_timeout_seconds"]

                # 1. LOGICA LUCI: Le luci standard dipendono SOLO dalla presenza
                self._dispatch_by_type(room, "lights", is_occupied)

                # 2. LOGICA HVAC (CONDIZIONATORE E RISCALDAMENTO)
                if room in self.temp_windows and len(self.temp_windows[room]) > 0:
                    t_mean = sum(self.temp_windows[room]) / len(self.temp_windows[room])
                    
                    if is_occupied:
                        # --- MODALITÀ COMFORT (Stanza Occupata) ---
                        if t_mean > self.target_temp:
                            self._dispatch_by_type(room, "fan", 75)       # Accende Condizionatore
                            self._dispatch_by_type(room, "heater", False) # Spegne Termosifone
                            self._dispatch_by_type(room, "lcd", f"T:{t_mean:.1f}C AC:75%")
                        elif t_mean < self.target_temp - 2.0:             # Soglia per il freddo
                            self._dispatch_by_type(room, "fan", 0)        # Spegne Condizionatore
                            self._dispatch_by_type(room, "heater", True)  # Accende Termosifone
                            self._dispatch_by_type(room, "lcd", f"T:{t_mean:.1f}C HEAT:ON")
                        else:
                            self._dispatch_by_type(room, "fan", 0)
                            self._dispatch_by_type(room, "heater", False)
                            self._dispatch_by_type(room, "lcd", f"T:{t_mean:.1f}C OK")
                    
                    else:
                        # --- MODALITÀ ECO (Stanza Vuota) ---
                        if t_mean > self.critical_temp:
                            # Previene surriscaldamenti severi (Emergenza server/hardware)
                            alert = {"room": room, "alert": "TEMP_CRITICAL", "mean": round(t_mean, 2)}
                            self.client.publish(self.alert_topic, json.dumps(alert))
                            self._dispatch_by_type(room, "fan", 100)
                            self._dispatch_by_type(room, "heater", False)
                            self._dispatch_by_type(room, "lcd", f"T:{t_mean:.1f}C ECO:COOL")
                            
                        elif t_mean < 15.0:
                            # Previene il congelamento dei tubi (Antigelo)
                            self._dispatch_by_type(room, "fan", 0)
                            self._dispatch_by_type(room, "heater", True)
                            self._dispatch_by_type(room, "lcd", f"T:{t_mean:.1f}C ECO:HEAT")
                            
                        else:
                            # Temperatura accettabile in risparmio energetico
                            self._dispatch_by_type(room, "fan", 0)
                            self._dispatch_by_type(room, "heater", False)
                            self._dispatch_by_type(room, "lcd", f"T:{t_mean:.1f}C ECO:IDLE")

        except Exception as e:
            print(f"[ERRORE CONTROLLER] {e}")

    def start(self):
        self._get_broker_loop()
        threading.Thread(target=self.register_and_keep_alive, daemon=True).start()
        threading.Thread(target=self._sync_topology, daemon=True).start()
        
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.is_running = False
            self.client.disconnect()

if __name__ == "__main__":
    controller = SmartHomeController()
    controller.start()
