import cherrypy

# 1. Importiamo le classi dai file dei singoli esercizi
# (Modifica i nomi dei file se li hai salvati in modo diverso)
from sensor_reading_webserver import *
#from esercizio_03 import ActuatorService
from LoggerService import *
#from ex3 import *

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

    # 3. Hosting Multiple Applications: montiamo ogni esercizio su un percorso base differente
    cherrypy.tree.mount(SensorReadingWebserver(), '/sensors', conf)
    #cherrypy.tree.mount(ActuatorService(), '/es3', conf)
    cherrypy.tree.mount(LoggerService(), "/log", conf)
    #cherrypy.tree.mount(SmartHomeActuators(), "/rooms", conf)

    # 4. Impostiamo l'host e la porta
    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': 8080})

    # 5. Avviamo il server in modalità bloccante
    cherrypy.engine.start()
    cherrypy.engine.block()