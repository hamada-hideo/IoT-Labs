import cherrypy
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
DIR = os.path.dirname(os.path.abspath(__file__))

from LoggerWebServer.logger_webserver import LoggerWebServer

if __name__ == '__main__':
    with open(os.path.join(DIR, "network_config.json")) as f:
        data = json.load(f)
    ip = data["ip"]
    port = data["port"]
    endpoint = data["endpoint"]
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

    cherrypy.tree.mount(LoggerWebServer(ip, port, endpoint), f"/{endpoint}", conf)

    # 4. Impostiamo l'host e la porta
    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': port})

    # 5. Avviamo il server in modalità bloccante
    cherrypy.engine.start()
    cherrypy.engine.block()