import cherrypy
import random
import time
import json
import requests


class ArduinoLogWebServer(object):
    exposed = True
    def __init__(self):
        self.sensor_logs=[]
    def POST(self, *uri, **params):
        clean_uri = [u.strip() for u in uri if u.strip() != ""]
        if len(clean_uri) > 0 and clean_uri[0] == "log":
            cl = cherrypy.request.headers.get('Content-Length', 0)
            rawbody = cherrypy.request.body.read(int(cl))
            try:
                incoming_data = json.loads(rawbody)
                self.sensor_logs.append(incoming_data)
                return json.dumps({"status": "success", "message": "Log saved" }).encode('utf-8')
            except json.JSONDecodeError:
                raise cherrypy.HTTPError(400, "formato JSON non valido")
        else:
            raise cherrypy.HTTPError(404, "endpoint non trovato. Usa /log per inviare i dati")
    def GET(self, *uri, **params):
        clean_uri = [u.strip() for u in uri if u.strip() != ""]
        if len(clean_uri) > 0 and clean_uri[0] == "log":
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(self.sensor_logs).encode('utf-8')
        else:
            raise cherrypy.HTTPError(404, "endpoint non trovato. Usa /log per inviare i dati")
