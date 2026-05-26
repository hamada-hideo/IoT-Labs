import cherrypy
import random
import time
import json
import requests
import threading
import SenMLUtils as SenML
from Catalog.catalog_client import *

class SensorReadingWebServer(object):
    exposed = True

    def __init__(self, ip, port, endpoint):

        self.rooms = ["living_room", "kitchen", "bedroom"]
        self.sensor_types = {
            "temperature": "Cel", 
            "humidity": "%RH", 
            "motion": "bool"
        }

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

        self.cc = CatalogClient()

        threading.Thread(target=self.cc.try_register_refresh_loop, args = (self.data, self.id), daemon=True).start()

        self.logger_url_valid = False
        
        threading.Thread(target=self._try_get_url, args = ("LoggerWebServer",), daemon=True).start()

    def _try_get_url(self, id):
        while True:
            time.sleep(self.cc.loop_time)
            if not self.logger_url_valid:
                res = self.cc.get_service(id)
                if res:
                    self.logger_url = res["rest"]["url"]
                    self.logger_url_valid = True

    def _build_resource_list(self):
        res = dict()
        for room in self.rooms:
            res[room] = dict()
            for sensor in self.sensor_types:
                res[room][sensor] = {
                    "type": sensor,
                    "unit": self.sensor_types[sensor]
                }
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
                sensor_name = st if is_room_specific else f"{r}/{st}"
                val = self._simulate_value(st)
                events.append(SenML.build_event_dict(sensor_name, self.sensor_types[st], val, delta_t))
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

        if req_room and req_room not in self.rooms:
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found"}))
        if req_type and req_type not in self.sensor_types:
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown sensor type"}))

        rooms_to_read = [req_room] if req_room else self.rooms
        sensors_to_read = [req_type] if req_type else list(self.sensor_types.keys())
        
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
                # Effettuiamo una POST locale all'endpoint del logger (es. porta 8080)
                response = requests.post(self.logger_url, json=senml_document, timeout=2)
                if response.status_code != 200:
                    print(f"Attenzione: Impossibile salvare il log. Risposta del server: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                # Se il logger è spento, stampiamo l'errore su console 
                # ma non facciamo crashare il server sensori
                print(f"Attenzione: Impossibile salvare il log. Errore: {e}")
        else:
            print(f"Attenzione: Impossibile salvare il log. Non è stato possibile ottenere l'url del logger.")

        # Risposta finale al client che ha fatto la GET
        return json.dumps(senml_document).encode('utf-8')
