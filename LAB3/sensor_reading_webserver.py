import cherrypy
import random
import time
import json
import requests
from Globals import *
import SenMLUtils as SenML

class SensorReadingWebserver(object):
    exposed = True
    
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
                events.append(SenML.build_event_dict(sensor_name, SENSOR_TYPES[st], val, delta_t))
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

        if req_room and req_room not in ROOMS:
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found"}))
        if req_type and req_type not in SENSOR_TYPES:
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown sensor type"}))

        rooms_to_read = [req_room] if req_room else ROOMS
        sensors_to_read = [req_type] if req_type else list(SENSOR_TYPES.keys())
        
        if req_room:
            base_name = f"smart_home/{req_room}/"
            is_room_specific = True
        else:
            base_name = "smart_home/"
            is_room_specific = False
            
        events_array = self._generate_senml_events(rooms_to_read, sensors_to_read, is_room_specific)
        senml_document = SenML.build_array_dict(base_name, float(time.time()), events_array)

        try:
            # Effettuiamo una POST locale all'endpoint del logger (es. porta 8080)
            requests.post("http://127.0.0.1:8080/log", json=senml_document, timeout=2)
        except requests.exceptions.RequestException as e:
            # Se il logger è spento, stampiamo l'errore su console 
            # ma non facciamo crashare il server sensori
            print(f"Attenzione: Impossibile salvare il log. Errore: {e}")

        # Risposta finale al client che ha fatto la GET
        return json.dumps(senml_document).encode('utf-8')