import cherrypy
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from Globals import *
from SensorReadingActuatorControlWebServer.sensor_reading_webserver import SensorReadingWebServer
from SensorReadingActuatorControlWebServer.actuator_control_webserver import ActuatorControlWebServer

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
    cherrypy.tree.mount(SensorReadingWebServer(), '/sensors', conf)
    cherrypy.tree.mount(ActuatorControlWebServer(), '/actuators', conf)
    
    cherrypy.config.update({'server.socket_host': SENSOR_READING_ACTUATOR_CONTROL_WEBSERVER_IP})
    cherrypy.config.update({'server.socket_port': SENSOR_READING_ACTUATOR_CONTROL_WEBSERVER_PORT})
    
    cherrypy.engine.start()
    cherrypy.engine.block()