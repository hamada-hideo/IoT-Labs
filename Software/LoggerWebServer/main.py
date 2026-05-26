import cherrypy
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from LoggerWebServer.logger_webserver import LoggerWebServer

IP = "127.0.0.1"
PORT = 8082
ENDPOINT = "log"

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

    cherrypy.tree.mount(LoggerWebServer(IP, PORT, ENDPOINT), f"/{ENDPOINT}", conf)

    # 4. Impostiamo l'host e la porta
    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': PORT})

    # 5. Avviamo il server in modalità bloccante
    cherrypy.engine.start()
    cherrypy.engine.block()