# EXERCISE: Exercise 06 / Exercise 09 Extension - Sensor REST Web Server
# ACTOR: SensorReadingWebServer (Centralized Sensor Telemetry Core)
# DESCRIPTION: Manages and simulates physical smart home sensor nodes. Exposes 
#              a REST API for environmental polling, translates raw streams into 
#              SenML arrays, synchronizes logs with the historical database, and 
#              clones data events directly to MQTT distribution channels.

# SECTION 1: SYSTEM UTILITIES & DEPENDENCY OVERLAYS
import cherrypy
import random
import time
import json
import requests
import threading
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import SenMLUtils as SenML
from Catalog.catalog_client import *
# Importiamo il nuovo bridge creato
from SensorReadingActuatorControlWebServer.mqtt_sensors_bridge import MQTTSensorsBridge

DIR = os.path.dirname(os.path.abspath(__file__))
# SECTION 2: CLASS INITIALIZATION & COMPONENT LINKAGE
class SensorReadingWebServer(object):
    exposed = True

    def __init__(self, ip, port, endpoint):
        """
        Constructor method. Loads sensor layout resources, builds descriptive profiles,
        maps endpoints, and kicks off parallel threads for logging synchronization and MQTT.
        """
        with open(os.path.join(DIR, "sensors_config.json"), "r") as f:
            self.resources = json.load(f)
        self.sensor_types = self._build_sensor_types()

        self.ip = ip
        self.port = port
        self.endpoint = endpoint
        self.id = "SensorReadingWebServer"
        self.logger_id = "LoggerWebServer"

        self.devices_list = self._build_devices_list()
        
        self.data = {
            "id": self.id,
            "description": "Service that exposes reads from the smart home sensors",
            "rest": {
                "url": f"http://{self.ip}:{self.port}/{self.endpoint}"
            },
            "resources": self._build_resource_list()
        }
        self.registered = False

        self.cc = CatalogClient()

        threading.Thread(target=self._try_register_refresh_loop, daemon=True).start()

        self.logger_url_valid = False
        threading.Thread(target=self._try_get_logger_url, daemon=True).start()

        # Inizializza e lancia in parallelo il bridge MQTT per la telemetria
        self.mqtt_bridge = MQTTSensorsBridge(self)
        threading.Thread(target=self.mqtt_bridge.run, daemon=True).start()

        # SECTION 3: AUTOMATED MAINTENANCE & PROFILE GENERATION RUNNERS
    def _try_register_refresh_loop(self):
        """
        Maintains structural availability states inside the central Catalog system
        for both this collection server module and all embedded sub-devices.
        """
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

    def _try_get_logger_url(self):
        """
        Queries the central registry ecosystem continuously to dynamically establish 
        and mount the active connection coordinates of the central Logger database service.
        """
        while True:
            time.sleep(self.cc.loop_time)
            res = self.cc.get_service(self.logger_id)
            if res:
                url = res["rest"]["url"]
                self.logger_url = url
                self.logger_url_valid = True
                break

    def _build_sensor_types(self):
        """Extracts unique environmental capability identifiers present across all rooms."""
        res = set()
        for room in self.resources:
            for sensor in self.resources[room]:
                res.add(self.resources[room][sensor]["type"])
        return [t for t in res]

    def _build_devices_list(self):
        """Constructs an exhaustive catalog blueprint dictionary for individual sensor registration."""
        res = []
        for room in self.resources:
            for sensor in self.resources[room]:
                res.append({
                    "device": {
                        "id": f"{room}/{sensor}",
                        "description": f"{sensor} sensor located in room {room}",
                        "resources": self.resources[room][sensor],
                        "rest": {
                            "url": f"http://{self.ip}:{self.port}/{self.endpoint}/{room}/{sensor}"
                        }
                    },
                    "registered": False
                })
        return res

    def _build_resource_list(self):
        """Generates a brief structure mapping spatial units to local sensor token IDs."""
        res = dict()
        for room in self.resources:
            res[room] = [s for s in self.resources[room]]
        return res
    # SECTION 4: DATA SIMULATION & EXTENDED SENML GENERATION LAYERS
    def _simulate_value(self, s_type):
        """Simulates environmental measurements within configured realistic boundary parameters."""
        if s_type == "temperature": 
            return round(random.uniform(15.0, 30.0), 1)
        elif s_type == "humidity": 
            return round(random.uniform(30.0, 70.0), 1)
        elif s_type == "motion": 
            return random.choice([True, False])
        return 0

    def _generate_senml_events(self, rooms_to_read, sensors_to_read, is_room_specific):
        """
        Generates individual data event instances, builds metric types, and packages 
        measurements across sequential delta timeline streams.
        """
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
     # SECTION 5: HTTP REST ENDPOINTS (POLLING READ INTERACTION)
    def GET(self, *uri, **params):
        """
        Handles HTTP GET requests. Parses routing contexts to filter sensor events,
        packages telemetry into SenML outputs, and clones transactions across REST and MQTT.
        """
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

        if self.logger_url_valid:
            try:
                
                response = requests.post(self.logger_url, json=senml_document, timeout=2)
                if response.status_code != 200:
                    print(f"Attenzione: Impossibile salvare il log. Risposta del server: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
               
                print(f"Attenzione: Impossibile salvare il log. Errore: {e}")
                self.logger_url_valid = False
                
                
                threading.Thread(target=self._try_get_logger_url, daemon=True).start()
        else:
            print(f"Attenzione: Impossibile salvare il log. Non è stato possibile ottenere l'url del logger.")

       
        self.mqtt_bridge.publish_telemetry(senml_document)

        return json.dumps(senml_document).encode('utf-8')
