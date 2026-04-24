import cherrypy
import requests

class SmartHomeSensorService:
    exposed=True

    def GET(self):
        



if "__name__" == "__main__":
    
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content Type',
            'applications/json')]
            }

    }
    cherrypy.tree.mount(MyService(),'/',conf)
    cherrypy.config.update(('server.socket_port':9090])
    cherrypy.engine.start()
    cherrypy.engine.block()

    
