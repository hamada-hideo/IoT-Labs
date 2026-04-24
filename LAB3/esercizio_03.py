import cherrypy
import random
import time
import json
class ActuatorService(object):
    exposed = True

    def __init__(self):
        # Dizionario di stato in memoria per salvare lo stato degli attuatori [7]
        self.actuators = {
            "living_room": {"thermostat": 20.0, "lights": False, "blinds": 0},
            "kitchen": {"thermostat": 20.0, "lights": False, "blinds": 0},
            "bedroom": {"thermostat": 20.0, "lights": False, "blinds": 0}
        }

    # Restituisce lo stato attuale dell'attuatore [6]
    def GET(self, *uri, **params):
        if len(uri) != 2:
            raise cherrypy.HTTPError(400, "URI format: /<room>/<device>")
        room, device = uri, uri[5]
        
        if room not in self.actuators or device not in self.actuators[room]:
            raise cherrypy.HTTPError(404, "Room or device not found")

        senml_payload = [{"bn": f"{room}/", "n": device, "v": self.actuators[room][device], "bt": time.time()}]
        return json.dumps(senml_payload).encode('utf-8')

    # Riceve il payload JSON SenML e modifica lo stato dell'attuatore [6]
    def PUT(self, *uri, **params):
        if len(uri) != 2:
            raise cherrypy.HTTPError(400, "URI format: /<room>/<device>")
        room, device = uri, uri[5]
        
        if room not in self.actuators or device not in self.actuators[room]:
            raise cherrypy.HTTPError(404, "Room or device not found")
        
        body = cherrypy.request.body.read()
        try:
            data = json.loads(body)
            # Dobbiamo assicurarci di leggere il campo 'v' dal primo elemento dell'array SenML
            new_value = data['v']
        except (ValueError, KeyError, IndexError):
            # Errore 422 se il payload inviato è malformato [7]
            raise cherrypy.HTTPError(422, "Malformed SenML payload")
        
        # Limiti di sicurezza: se il termostato è fuori dal range 10-30°C restituisce un 400 [7]
        if device == "thermostat" and (new_value < 10.0 or new_value > 30.0):
            raise cherrypy.HTTPError(400, "Thermostat setpoint out of range (10-30)")
        
        # Salvataggio del nuovo stato
        self.actuators[room][device] = new_value
        
        senml_payload = [{"bn": f"{room}/", "n": device, "v": new_value, "bt": time.time()}]
        return json.dumps(senml_payload).encode('utf-8')