import cherrypy
import random
import time
import json

class SensorReadingWebserver(object):
    exposed = True
    def __init__(self):
        self.rooms = ["living_room", "kitchen", "bedroom"]
        self.sensor_types = {"temperature": "Cel", "humidity": "%RH", "motion": "bool"}
    def _simulate_value(self, s_type):
        if s_type == "temperature": 
            return round(random.uniform(15.0, 30.0), 1)
        elif s_type == "humidity": 
            return round(random.uniform(30.0, 70.0), 1)
        elif s_type == "motion": 
            return random.choice([True, False])
        return 0
    # FUNZIONE: Genera l'array degli eventi SenML
    def _generate_senml_events(self, rooms_to_read, sensors_to_read, is_room_specific):
        events = []
        delta_t = 0.0 
        for r in rooms_to_read:
            for st in sensors_to_read:
                sensor_name = st if is_room_specific else f"{r}/{st}"
                val = self._simulate_value(st)  
                events.append({
                    "n": sensor_name,
                    "u": self.sensor_types[st],
                    "t": delta_t,
                    "v": val
                })
                delta_t += 1.0    
        return events
    def GET(self, *uri, **params):
        # 1. CASE-SENSITIVE: .strip() per rimuovere gli spazi
        clean_uri = [u.strip() for u in uri if u.strip() != ""]
        req_room = None
        req_type = None
        # 2A. STRICT VALIDATION SUL PATH
        if len(clean_uri) > 2:
            raise cherrypy.HTTPError(400, "Formato URI errato: troppi segmenti.")
        # LOGICA URI PATH
        if len(clean_uri) > 0:
            req_room = clean_uri[0]
            if len(clean_uri) == 2:
                req_type = clean_uri[1]        
        # LOGICA QUERY PARAMETERS
        else:
            # 2B. STRICT VALIDATION SULLE QUERY
            allowed_params = {'room', 'type'}
            for key in params.keys():
                if key.strip() not in allowed_params:
                    raise cherrypy.HTTPError(400, f"Parametro query non supportato: '{key}'")

            if 'room' in params:
                req_room = params['room'].strip()
            if 'type' in params:
                req_type = params['type'].strip()
        # VALIDAZIONI CONTENUTO
        if req_room and req_room not in self.rooms:
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found"}))
            
        if req_type and req_type not in self.sensor_types:
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown sensor type"}))
        # ASSEMBLAGGIO FINALE DEL DOCUMENTO
        rooms_to_read = [req_room] if req_room else self.rooms
        sensors_to_read = [req_type] if req_type else list(self.sensor_types.keys())
        if req_room:
            base_name = f"smart_home/{req_room}/"
            is_room_specific = True
        else:
            base_name = "smart_home/"
            is_room_specific = False
        events_array = self._generate_senml_events(rooms_to_read, sensors_to_read, is_room_specific)
        senml_document = {
            "bn": base_name,
            "bt": float(time.time()), 
            "e": events_array
        }
        return json.dumps(senml_document).encode('utf-8')