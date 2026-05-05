import cherrypy
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from Globals import *
from LoggerWebServer.logger_webserver import LoggerWebServer

if __name__ == '__main__':
    # 2. Configurazione obbligatoria per abilitare i verbi HTTP REST (MethodDispatcher)
    # e impostare gli header JSON in uscita
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }

    cherrypy.tree.mount(LoggerWebServer(), "/log", conf)

    # 4. Impostiamo l'host e la porta
    cherrypy.config.update({'server.socket_host': LOGGER_WEBSERVICE_IP})
    cherrypy.config.update({'server.socket_port': LOGGER_WEBSERVICE_PORT})

    # 5. Avviamo il server in modalità bloccante
    cherrypy.engine.start()
    cherrypy.engine.block()