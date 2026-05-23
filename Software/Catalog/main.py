import cherrypy
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from Catalog.catalog_service import Catalog

if __name__ == '__main__':
    conf = {
        '/':{
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }
    cherrypy.tree.mount(Catalog(),'/catalog', conf)
    cherrypy.config.update({'server.socket_host':'0.0.0.0'})
    cherrypy.config.update({'server.socket_port':8080})
    print("Start of IoT Catalog on 8080...")
    cherrypy.engine.start()
    cherrypy.engine.block()
