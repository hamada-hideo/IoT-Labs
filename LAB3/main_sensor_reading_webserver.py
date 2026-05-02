import cherrypy
from sensor_reading_webserver import SensorReadingWebserver

if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }
    
    # Montiamo il webserver unificato
    cherrypy.tree.mount(SensorReadingWebserver(), '/sensors', conf)
    
    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': 8080})
    
    cherrypy.engine.start()
    cherrypy.engine.block()