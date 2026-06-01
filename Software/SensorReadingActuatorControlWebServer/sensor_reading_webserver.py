import cherrypy
import random
import time
import json
import threading
import os
import SenMLUtils as SenML
from Catalog.mqtt_catalog_client import MQTTCatalogClient

DIR = os.path.dirname(os.path.abspath(__file__))

class SensorReadingWebServer(object):
    exposed = True

    def __init__(self, ip, port, endpoint):
        with open(os.path.join(DIR, "sensors_config.json"), "r") as f:
            self.resources = json.load(f)
        self.sensor_types = self._build_sensor_types()
        self.devices_list = self._build_devices_list()

        self.ip = ip
        self.port = port
        self.endpoint = endpoint
        self.id = "SensorReadingWebServer"
        
        self.data = {
            "id": self.id,
            "description": "Service that exposes reads from the smart home sensors",
            "rest": {
                "url": f"http://{self.ip}:{self.port}/{self.endpoint}",
                "method": "GET"
            },
            "resources": self._build_resource_list()
        }
        self.registered = False

        self.cc = MQTTCatalogClient(self.id)
        self.cc.connect()

        threading.Thread(target=self._try_register_refresh_loop, daemon=True).start()

    def _try_register_refresh_loop(self):
        while True:
            time.sleep(self.cc.loop_time)
            if not self.registered:
                if self.cc.register_service(self.data):
                    self.registered = True
            else:
                if not self.cc.refresh_service(self.id):
                    self.registered = False
            for i in range(len(self.devices_list)):
                if not self.devices_list[i]["registered"]:
                    if self.cc.register_device(self.devices_list[i]["device"]):
                        self.devices_list[i]["registered"] = True
                else:
                    if not self.cc.refresh_device(self.devices_list[i]["device"]["id"]):
                        self.devices_list[i]["registered"] = False

    def _build_sensor_types(self):
        res = set()
        for room in self.resources:
            for sensor in self.resources[room]:
                res.add(self.resources[room][sensor]["type"])
        return [t for t in res]

    def _build_devices_list(self):
        res = []
        for room in self.resources:
            for sensor in self.resources[room]:
                res.append({
                    "device": {
                        "id": f"{room}-{sensor}",
                        "description": f"{sensor} sensor located in room {room}",
                        "resources": self.resources[room][sensor]
                    },
                    "registered": False
                })
        return res

    def _build_resource_list(self):
        res = dict()
        for room in self.resources:
            res[room] = [s for s in self.resources[room]]
        return res
    
    def _simulate_value(self, s_type):
        if s_type == "temperature": 
            return round(random.uniform(15.0, 30.0), 1)
        elif s_type == "humidity": 
            return round(random.uniform(30.0, 70.0), 1)
        elif s_type == "motion": 
            return random.choice([True, False])
        return 0

    def _generate_senml_events(self, rooms_to_read, sensors_to_read, is_room_specific):
        events = []
        delta_t = 0.0 
        for r in rooms_to_read:
            for st in sensors_to_read:
                for sensor in self.resources[r]:
                    if self.resources[r][sensor]["type"] == st:
                        sensor_name = sensor if is_room_specific else f"{r}/{sensor}"
                        val = self._simulate_value(st)
                        events.append(SenML.build_event_dict(sensor_name, self.resources[r][sensor]["unit"], val, delta_t))
                        delta_t += 1.0
        return events
        
    def GET(self, *uri, **params):
        clean_uri = [u.strip() for u in uri if u.strip() != ""]
        req_room = None
        req_type = None

        if len(clean_uri) > 2:
            raise cherrypy.HTTPError(400, "Formato URI errato: troppi segmenti.")

        if len(clean_uri) > 0:
            req_room = clean_uri[0]
            if len(clean_uri) == 2:
                req_type = clean_uri[1]
        else:
            allowed_params = {'room', 'type'}
            for key in params.keys():
                if key.strip() not in allowed_params:
                    raise cherrypy.HTTPError(400, f"Parametro query non supportato: '{key}'")
            if 'room' in params:
                req_room = params['room'].strip()
            if 'type' in params:
                req_type = params['type'].strip()

        if req_room and req_room not in self.resources:
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found"}))
        if req_type and req_type not in self.sensor_types:
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown sensor type"}))
        if req_room and req_type and req_type not in [self.resources[req_room][s]["type"] for s in self.resources[req_room]]:
            raise cherrypy.HTTPError(404, json.dumps({"error": "no sensors of the given type in the given room"}))

        rooms_to_read = [req_room] if req_room else [r for r in self.resources]
        sensors_to_read = [req_type] if req_type else self.sensor_types
        
        if req_room:
            base_name = f"smart_home/{req_room}/"
            is_room_specific = True
        else:
            base_name = "smart_home/"
            is_room_specific = False
            
        events_array = self._generate_senml_events(rooms_to_read, sensors_to_read, is_room_specific)
        senml_document = SenML.build_array_dict(events_array, base_name, float(time.time()))

        # PUBBLICAZIONE MQTT AGGIUNTA QUI
        self.cc.client.publish("/tiot/group12/sensors/telemetry", json.dumps(senml_document))

        return json.dumps(senml_document).encode('utf-8')
