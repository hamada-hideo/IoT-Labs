import cherrypy
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
DIR = os.path.dirname(os.path.abspath(__file__))

from Catalog.catalog_service import Catalog

if __name__ == '__main__':

    with open(os.path.join(DIR, "config.json"), "r") as f:
        data = json.load(f)
    endpoint = data["rest"]["endpoint"]
    port = data["rest"]["port"]

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }
    
    # 1. Creation of catalog instance
    catalog_instance = Catalog()
    
    # 2. Catalog on Cherrypy
    cherrypy.tree.mount(catalog_instance, f'/{endpoint}', conf)
    cherrypy.config.update({'server.socket_host': '::'})
    cherrypy.config.update({'server.socket_port': port})
    
    # 4. starting CherryPy
    print("Start of IoT Catalog on 8080 with MQTT integration...")
    cherrypy.engine.start()
    cherrypy.engine.block()
