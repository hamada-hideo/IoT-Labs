import cherrypy
import random
import time
import json

class SensorServiceURI(object):
    exposed = True
    
    def __init__(self):
        self.rooms = ["living_room", "kitchen", "bedroom"]
        self.sensor_types = {"temperature": "Cel", "humidity": "%RH", "motion": "bool"}

    def GET(self, *uri, **params):
        
        # ========================================================
        # CASO 1: Zero segmenti (es. /es2/)
        # Mostra le stanze e i sensori disponibili [1]
        # ========================================================
        if len(uri) == 0:
            return json.dumps({
                "available_rooms": self.rooms,
                "available_sensors": list(self.sensor_types.keys())
            }).encode('utf-8')

        # Se il codice prosegue, significa che c'è almeno 1 segmento. 
        # Il primo segmento (indice 0) è sempre la stanza.
        room = uri[0]
        
        # Validazione della stanza (comune al Caso 2 e 3) [1]
        if room not in self.rooms:
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found"}))

        # ========================================================
        # CASO 2: Un segmento (es. /es2/bedroom)
        # Mostra TUTTI i sensori di quella specifica stanza [1]
        # ========================================================
        if len(uri) == 1:
            payload = []
            # Scorriamo tutti i sensori noti e generiamo un valore per ciascuno
            for s_type, unit in self.sensor_types.items():
                val = 0
                if s_type == "temperature": val = round(random.uniform(15.0, 30.0), 1)
                elif s_type == "humidity": val = round(random.uniform(30.0, 70.0), 1)
                elif s_type == "motion": val = random.choice([True, False])

                payload.append({
                    "bn": f"{room}/",
                    "n": s_type,
                    "u": unit,
                    "v": val,
                    "bt": time.time() 
                })
            return json.dumps(payload).encode('utf-8')

        # ========================================================
        # CASO 3: Due segmenti (es. /es2/bedroom/temperature)
        # Mostra solo il sensore richiesto [1]
        # ========================================================
        if len(uri) == 2:
            s_type = uri[1]
            
            # Validazione del tipo di sensore [1]
            if s_type not in self.sensor_types:
                raise cherrypy.HTTPError(400, json.dumps({"error": "unknown sensor type"}))
                
            # Generazione del singolo valore
            val = 0
            if s_type == "temperature": val = round(random.uniform(15.0, 30.0), 1)
            elif s_type == "humidity": val = round(random.uniform(30.0, 70.0), 1)
            elif s_type == "motion": val = random.choice([True, False])

            senml_payload = [{
                "bn": f"{room}/",
                "n": s_type,
                "u": self.sensor_types[s_type],
                "v": val,
                "bt": time.time() 
            }]
            return json.dumps(senml_payload).encode('utf-8')

        # ========================================================
        # CASO ERRORE: Più di 2 segmenti
        # ========================================================
        raise cherrypy.HTTPError(400, "URI format: /<room>/<type>")