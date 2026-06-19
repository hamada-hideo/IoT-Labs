import cherrypy
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
DIR = os.path.dirname(os.path.abspath(__file__))

from SensorReadingActuatorControlWebServer.sensor_reading_webserver import SensorReadingWebServer
from SensorReadingActuatorControlWebServer.actuator_control_webserver import ActuatorControlWebServer

if __name__ == '__main__':
    with open(os.path.join(DIR, "network_config.json")) as f:
        data = json.load(f)
    ip = data["ip"]
    port = data["port"]
    sensors_endpoint = data["sensors_endpoint"]
    actuators_endpoint = data["actuators_endpoint"]
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }
 
    cherrypy.tree.mount(SensorReadingWebServer(ip, port, sensors_endpoint), f'/{sensors_endpoint}', conf)
    cherrypy.tree.mount(ActuatorControlWebServer(ip, port, actuators_endpoint), f'/{actuators_endpoint}', conf)
    
    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': port})
    
    cherrypy.engine.start()
    cherrypy.engine.block()
