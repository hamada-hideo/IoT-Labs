import cherrypy
import json
import threading
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from Catalog.mqtt_catalog_bridge import *

DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_FILE = os.path.join(DIR, 'catalog.json')

class Catalog(object):
    exposed = True

    def __init__(self):
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
        self.cleanup_time = data["expiration_time"]
        self.broker = data["mqtt"]["broker"]
        
        self.lock = threading.Lock()
        
        self.catalog = {
            "broker": self.broker,
            "devices": {},
            "services": {}
        }
        
        self._load_catalog()
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

        self.mqtt_bridge = MQTTCatalogBridge(self)
        threading.Thread(target=self.mqtt_bridge.run, daemon=True).start()

    def _load_catalog(self):
        with self.lock:
            if os.path.exists(CATALOG_FILE):
                try:
                    with open(CATALOG_FILE, 'r') as f:
                        self.catalog = json.load(f)   
                    if 'devices' not in self.catalog:
                        self.catalog['devices'] = {}
                    if 'services' not in self.catalog:
                        self.catalog['services'] = {}
                    
                    self.catalog['broker'] = self.broker
                except json.JSONDecodeError:
                    self._save_catalog() 
            else:
                self._save_catalog()

    def _save_catalog(self):
        with open(CATALOG_FILE, 'w') as f:
            json.dump(self.catalog, f, indent=4)

    def _cleanup_loop(self):
        while True:
            time.sleep(self.cleanup_time // 2)
            current_time = time.time()
            with self.lock:
                cleaned = False
                for category in ['devices', 'services']:
                    to_delete = []
                    for item_id, info in self.catalog[category].items():
                        if current_time - info.get('insert_timestamp', 0) > self.cleanup_time:
                            to_delete.append(item_id)     
                    for item_id in to_delete:
                        del self.catalog[category][item_id]
                        cleaned = True                        
                if cleaned:
                    print(f"[{time.strftime('%X')}] CLEANUP Removed record from catalog")
                    self._save_catalog() 

    @cherrypy.tools.json_out()
    def GET(self, *path, **params):
        with self.lock:  
            if not path:
                return self.catalog    
            category = path[0]
            if category == 'broker':
                return self.catalog.get('broker', {})
            elif category in ['devices', 'services']:
                if len(path) == 1:
                    return self.catalog[category]
                # --- FIX: Accetta percorsi >= 2 per ID con gli slash ---
                elif len(path) >= 2:
                    item_id = "/".join(path[1:]) # Ricuce living_room/thermostat
                    if item_id in self.catalog[category]:
                        return self.catalog[category][item_id]
                    else:
                        raise cherrypy.HTTPError(404, "Record not found")        
            raise cherrypy.HTTPError(400, "Invalid request")

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *path, **params):
        if not path or path[0] not in ['devices', 'services']:
             raise cherrypy.HTTPError(400, "Invalid category. Use /devices or /services")
        category = path[0] 
        data = cherrypy.request.json
        item_id = data.get('id') 
        if not item_id:
            raise cherrypy.HTTPError(400, "Payload must contain an 'id' field")
        with self.lock:
            if item_id in self.catalog[category]:
                self.catalog[category][item_id] = data
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                message = f"ID {item_id} aggiornato con successo"
            else:
                self.catalog[category][item_id] = data
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                message = f"Nuovo ID {item_id} registrato con successo"
            self._save_catalog()
        return {"status": "success", "message": message}

    @cherrypy.tools.json_out()
    def PUT(self, *path, **params):
        # --- FIX: Accetta percorsi lunghi e ricuce l'ID ---
        if len(path) < 2 or path[0] not in ['devices', 'services']:
            raise cherrypy.HTTPError(400, "Usa la sintassi PUT /devices/{id} o /services/{id} per il refresh")
        
        category = path[0]
        item_id = "/".join(path[1:]) # Ricuce living_room/thermostat
        
        with self.lock:
            if item_id in self.catalog[category]:
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                self._save_catalog()
                return {"status": "success", "message": f"Refresh di {item_id} effettuato con successo."}
            else:
                raise cherrypy.HTTPError(404, f"{item_id} non trovato o scaduto. Necessaria nuova registrazione via POST.")
