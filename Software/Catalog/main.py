import cherrypy
import os
import sys
import threading # <--- Fondamentale per far girare REST e MQTT insieme
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
DIR = os.path.dirname(os.path.abspath(__file__))

from Catalog.catalog_service import Catalog
# Importiamo la funzione di avvio del bridge MQTT
from Catalog.mqtt_catalog_bridge import start_mqtt_bridge

if __name__ == '__main__':

    with open(os.path.join(DIR, "network_config.json"), "r") as f:
        data = json.load(f)
    endpoint = data["endpoint"]
    port = data["port"]

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }
    
    # 1. Creiamo l'istanza unica del Catalogo
    catalog_instance = Catalog()
    
    # 2. Montiamo il catalogo su CherryPy
    cherrypy.tree.mount(catalog_instance, f'/{endpoint}', conf)
    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': port})
    
    # 3. FACCIAMO PARTIRE IL BRIDGE MQTT SU UN THREAD SEPARATO
    # Passiamo l'istanza del catalogo in modo che MQTT e REST lavorino sugli STESSI dati!
    mqtt_thread = threading.Thread(target=start_mqtt_bridge, args=(catalog_instance,))
    mqtt_thread.daemon = True # Si chiude automaticamente quando spegni il main
    mqtt_thread.start()
    
    # 4. Avviamo CherryPy
    print("Start of IoT Catalog on 8080 with MQTT integration...")
    cherrypy.engine.start()
    cherrypy.engine.block()