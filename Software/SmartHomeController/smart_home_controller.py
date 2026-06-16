import paho.mqtt.client as mqtt
import json
import time
import threading
import os
import sys
from collections import deque

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
        self.client_id = f"Controller_Group12_{int(time.time())}"

        self.home_topology = {} 
        self.temp_windows = {}
        self.presence_timers = {} 

        self.LLT1, self.HLT1 = 15, 20
        self.LLT2, self.HLT2 = 17, 22
        self.LFT1, self.HFT1 = 20, 30
        self.LFT2, self.HFT2 = 22, 32

        self.lcd_data = {}
        self.lcd_screen_index = 0

        self.cc = CatalogClient()
        self.registered = False
        self.service_payload = {
            "id": "smart_home_controller",
            "description": "Rule Engine: Pure Edge Toggle & Proportional HVAC",
            "endpoints": [self.sub_topic]
        }
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.is_running = True

    def _get_broker_loop(self):
        while self.is_running:
            broker = self.cc.get_broker()
            if broker:
                self.broker_host, self.broker_port = broker["ip"], broker["port"]
                break
            time.sleep(self.cc.loop_time)

    def _sync_topology(self):
        while self.is_running:
            try:
                devices = self.cc.get_devices()
                if devices and "error" not in devices:
                    device_list = devices if isinstance(devices, list) else devices.values() if isinstance(devices, dict) else []
                    for dev_info in device_list:
                        if not isinstance(dev_info, dict): continue
                        parts = dev_info.get("id", "").split("/")
                        if len(parts) >= 2:
                            room, dev_name = parts[0], parts[1]
                            
                            # FIX AMNESIA: Aggiungiamo i dispositivi, ma NON li rimuoviamo mai se il catalogo singhiozza
                            if room not in self.home_topology: 
                                self.home_topology[room] = {"sensors": {}, "actuators": {}}
                            
                            res_type = dev_info.get("resources", {}).get("type", dev_name)
                            if "mqtt" in dev_info and "command_topic" in dev_info["mqtt"]:
                                self.home_topology[room]["actuators"][dev_name] = {"type": res_type, "unit": dev_info.get("resources", {}).get("unit", ""), "command_topic": dev_info["mqtt"]["command_topic"]}
                            else:
                                self.home_topology[room]["sensors"][dev_name] = {"type": res_type}
                                
                    if self.home_topology and not hasattr(self, '_topology_printed'):
                        print(f"\n[CATALOGO] Mappa caricata (Amnesia Protetta): {list(self.home_topology.keys())}\n")
                        self._topology_printed = True
            except: pass
            time.sleep(getattr(self.cc, 'loop_time', 5))

    def _lcd_rotation_loop(self):
        while self.is_running:
            try:
                time.sleep(5)
                if not self.home_topology or not self.lcd_data: continue
                    
                for room, data in list(self.lcd_data.items()):
                    idx = self.lcd_screen_index
                    if idx == 0:
                        text = f"Temperature:|{int(data['temp'])}"
                    elif idx == 1:
                        text = f"Fan %:{int(data['fan'])}|Heater %:{int(data['heater'])}"
                    elif idx == 2:
                        text = f"Presence: {data['presence']}|"
                    elif idx == 3:
                        text = f" LEDS     FAN   |{data['llt']} {data['hlt']}    {data['lft']} {data['hft']}"
                    self._dispatch_by_type(room, "lcd", text)
                self.lcd_screen_index = (self.lcd_screen_index + 1) % 4
            except Exception as e:
                print(f"[ERRORE LCD THREAD] {e}")

    def register_and_keep_alive(self):
        while self.is_running:
            try:
                if not self.registered:
                    if self.cc.register_service(self.service_payload): self.registered = True
                else:
                    if not self.cc.refresh_service(self.service_payload["id"]): self.registered = False
            except: pass
            time.sleep(self.cc.loop_time)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] Iscritto al topic: {self.sub_topic}")
            self.client.subscribe(self.sub_topic)

    def send_command(self, room, actuator_id, actuator_info, value, override_id=None):
        base_name = f"smart_home/{room}/"
        final_id = override_id if override_id else actuator_id
        payload = SenML.build_array_dict([SenML.build_event_dict(final_id, actuator_info["unit"], value, time.time())], basename=base_name)
        self.client.publish(actuator_info["command_topic"], json.dumps(payload))

    def _dispatch_by_type(self, room, target_type, value):
        room_actuators = self.home_topology.get(room, {}).get("actuators", {})
        for act_id, act_info in room_actuators.items():
            if act_info["type"] == target_type:
                self.send_command(room, act_id, act_info, value)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            
            if not SenML.validate_SenML(payload):
                print("[AVVISO] Validazione SenML bypassata per tolleranza errori.")
                
            flat_events = SenML.flatten_senml(payload)
            rooms_to_process = set()

            for event in flat_events:
                # print(f"[RETE] Ricevuto: {event['n']} -> {event['v']}")
                
                name_parts = [p for p in event["n"].split("/") if p]
                if "smart_home" in name_parts:
                    idx = name_parts.index("smart_home")
                    if len(name_parts) >= idx + 3:
                        room, sensor_id = name_parts[idx + 1], name_parts[idx + 2]
                        val = event["v"]
                        
                        sensor_type = self.home_topology.get(room, {}).get("sensors", {}).get(sensor_id, {}).get("type", sensor_id)
                        is_active = str(val).lower() in ["true", "1", "on"]

                        if sensor_type == "temperature":
                            rooms_to_process.add(room)
                            if room not in self.temp_windows: self.temp_windows[room] = deque(maxlen=self.config["rolling_window_size"])
                            self.temp_windows[room].append(float(val))
                        
                        elif sensor_type == "motion" and is_active:
                            rooms_to_process.add(room)
                            self.presence_timers[room] = time.time()
                            
                        elif sensor_type == "noise_event" and is_active:
                            rooms_to_process.add(room)
                            self.presence_timers[room] = time.time() 
                            
                            room_acts = self.home_topology.get(room, {}).get("actuators", {})
                            for act_id, act_info in room_acts.items():
                                if act_info["type"] == "green_lights":
                                    self.send_command(room, act_id, act_info, True, override_id=f"{act_id}_toggle")
                                    print(f"> [TOGGLE EMESSO] {room} green_lights")

            for room in rooms_to_process:
                presence = (time.time() - self.presence_timers.get(room, 0)) < 1800 

                if presence:
                    lowLedTemp, highLedTemp = self.LLT1, self.HLT1
                    lowFanTemp, highFanTemp = self.LFT1, self.HFT1
                    presence_string = "Y"
                else:
                    lowLedTemp, highLedTemp = self.LLT2, self.HLT2
                    lowFanTemp, highFanTemp = self.LFT2, self.HFT2
                    presence_string = "N"

                if room in self.temp_windows and len(self.temp_windows[room]) > 0:
                    temperature = sum(self.temp_windows[room]) / len(self.temp_windows[room])
                else:
                    temperature = 25.0

                if temperature >= highFanTemp: fanPercent = 100
                elif temperature <= lowFanTemp: fanPercent = 0
                else: fanPercent = int(((temperature - lowFanTemp) / (highFanTemp - lowFanTemp)) * 100)

                if temperature >= highLedTemp: heaterPercent = 0
                elif temperature <= lowLedTemp: heaterPercent = 100
                else: heaterPercent = int(100 - (((temperature - lowLedTemp) / (highLedTemp - lowLedTemp)) * 100))

                self._dispatch_by_type(room, "fan", fanPercent)
                self._dispatch_by_type(room, "heater", heaterPercent)

                self.lcd_data[room] = {
                    "temp": temperature, "fan": fanPercent, "heater": heaterPercent, "presence": presence_string,
                    "llt": lowLedTemp, "hlt": highLedTemp, "lft": lowFanTemp, "hft": highFanTemp
                }
        except Exception as e:
            print(f"[ERRORE CONTROLLER] {e}")

    def start(self):
        self._get_broker_loop()
        threading.Thread(target=self.register_and_keep_alive, daemon=True).start()
        threading.Thread(target=self._sync_topology, daemon=True).start()
        threading.Thread(target=self._lcd_rotation_loop, daemon=True).start()
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            self.is_running = False
            self.client.disconnect()

if __name__ == "__main__":
    controller = SmartHomeController()
    controller.start()
