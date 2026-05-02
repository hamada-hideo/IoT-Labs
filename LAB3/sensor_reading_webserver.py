import cherrypy
import random
import time
import json

class SensorReadingWebserver(object):
    exposed = True
    
    def __init__(self):
        self.rooms = ["living_room", "kitchen", "bedroom"]
        self.sensor_types = {"temperature": "Cel", "humidity": "%RH", "motion": ""}

    def _simulate_value(self, s_type):
        if s_type == "temperature": 
            return round(random.uniform(15.0, 30.0), 1)
        elif s_type == "humidity": 
            return round(random.uniform(30.0, 70.0), 1)
        elif s_type == "motion": 
            return random.choice([True, False])
        return 0

    def GET(self, *uri, **params):
        clean_uri = [u.lower().strip() for u in uri if u.strip() != ""]
        
        req_room = None
        req_type = None

        # ========================================================
        # LOGICA ESERCIZIO 02: Parsing tramite URI Path
        # ========================================================
        if len(clean_uri) > 0:
            req_room = clean_uri[0]
            if len(clean_uri) == 2:
                req_type = clean_uri[1]
            elif len(clean_uri) > 2:
                raise cherrypy.HTTPError(400, "Formato URI errato")
                
        # ========================================================
        # LOGICA ESERCIZIO 01: Parsing tramite Query Parameters
        # ========================================================
        else:
            if 'room' in params:
                req_room = params['room'].lower().strip()
            if 'type' in params:
                req_type = params['type'].lower().strip()

        # ========================================================
        # VALIDAZIONI
        # ========================================================
        if req_room and req_room not in self.rooms:
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found", "available_rooms": self.rooms}))
            
        if req_type and req_type not in self.sensor_types:
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown sensor type", "valid_sensor_types": [x for x in self.sensor_types.keys()]}))

        # ========================================================
        # GENERAZIONE FORMATO SenML
        # ========================================================
        rooms_to_read = [req_room] if req_room else self.rooms
        sensors_to_read = [req_type] if req_type else list(self.sensor_types.keys())

        base_name = f"{req_room}/" if req_room else "smart_home/"
        
        senml_document = {
            "bn": base_name,
            # time.time() restituisce nativamente un float [2]
            "bt": float(time.time()), 
            "e": []
        }

        # Impostiamo il delta-time di partenza come float
        delta_t = 0.0 
        
        for r in rooms_to_read:
            for st in sensors_to_read:
                sensor_name = st if req_room else f"{r}/{st}"
                val = self._simulate_value(st)
                
                senml_document["e"].append({
                    "n": sensor_name,
                    "u": self.sensor_types[st],
                    "t": delta_t,
                    "v": val
                })
                delta_t += 1.0

        return json.dumps(senml_document).encode('utf-8')