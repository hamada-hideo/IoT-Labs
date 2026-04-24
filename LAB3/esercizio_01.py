import cherrypy
import random
import time
import json

class SensorServiceQuery(object):
    exposed = True
    
    def __init__(self):
        # Definiamo le stanze e i tipi di sensori validi con le loro unità di misura
        self.rooms = ["living_room", "kitchen", "bedroom"]
        self.sensor_types = {"temperature": "Cel", "humidity": "%RH", "motion": "bool"}

    def GET(self, **params):
        # Estraiamo i parametri dalla query string
        room = params.get('room')
        s_type = params.get('type')
        
        # Validazione e gestione degli errori 404 e 400 come da specifiche
        if not room or not s_type:
            raise cherrypy.HTTPError(400, "Missing room or type query parameters")
        if room not in self.rooms:
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found", "available_rooms": self.rooms}))
        if s_type not in self.sensor_types:
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown sensor type", "valid_types": list(self.sensor_types.keys())}))
            
        # Simulazione dei dati del sensore all'interno di range realistici
        val = 0
        if s_type == "temperature": val = round(random.uniform(15.0, 30.0), 1)
        elif s_type == "humidity": val = round(random.uniform(30.0, 70.0), 1)
        elif s_type == "motion": val = random.choice([True, False])

        # Creazione del JSON nel rigoroso formato SenML
        # time.time() genera il timestamp (bt) in formato Unix epoch
        senml_payload = [{
            "bn": f"{room}/",
            "n": s_type,
            "u": self.sensor_types[s_type],
            "v": val,
            "bt": time.time() 
        }]
        
        return json.dumps(senml_payload).encode('utf-8')
