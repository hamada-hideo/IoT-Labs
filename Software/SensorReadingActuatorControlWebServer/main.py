import cherrypy
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from SensorReadingActuatorControlWebServer.sensor_reading_webserver import SensorReadingWebServer
from SensorReadingActuatorControlWebServer.actuator_control_webserver import ActuatorControlWebServer

IP = "127.0.0.1"
PORT = 8081
SENSORS_ENDPOINT = "sensors"
ACTUATORS_ENDPOINT = "actuators"

if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }
    # Montiamo il webserver unificato
    cherrypy.tree.mount(SensorReadingWebServer(IP, PORT, SENSORS_ENDPOINT), f'/{SENSORS_ENDPOINT}', conf)
    cherrypy.tree.mount(ActuatorControlWebServer(IP, PORT, ACTUATORS_ENDPOINT), f'/{ACTUATORS_ENDPOINT}', conf)
    
    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': PORT})
    
    cherrypy.engine.start()
    cherrypy.engine.block()