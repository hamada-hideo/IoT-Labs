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
        # Utilizzo un Lock per evitare race conditions durante lettura/scrittura
        self.lock = threading.Lock()
        # Struttura base del catalogo
        self.catalog = {
            "broker": self.broker,
            "devices": {},
            "services": {}
        }
        # Ricarica il catalogo dal file JSON all'avvio
        self._load_catalog()
        # Avvia il thread in background per la pulizia dei record obsoleti
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

        self.mqtt_bridge = MQTTCatalogBridge(self)
        threading.Thread(target=self.mqtt_bridge.run, daemon=True).start()

    def _load_catalog(self):
        with self.lock:
            if os.path.exists(CATALOG_FILE):
                try:
                    with open(CATALOG_FILE, 'r') as f:
                        self.catalog = json.load(f)   
                    # Controlli di integrità: assicura che le chiavi esistano sempre
                    if 'devices' not in self.catalog:
                        self.catalog['devices'] = {}
                    if 'services' not in self.catalog:
                        self.catalog['services'] = {}
                    # Sovrascrive sempre le info del broker con quelle hardcodate 
                    # (HiveMQ è molto più stabile di Eclipse per lo sviluppo IoT)
                    self.catalog['broker'] = self.broker
                except json.JSONDecodeError:
                    # Se il file è corrotto, lo ricrea da zero
                    self._save_catalog() 
            else:
                self._save_catalog()
    def _save_catalog(self):
        # NOTA: Questa funzione presuppone che il thread chiamante 
        # abbia GIÀ acquisito self.lock (usando 'with self.lock:')
        # per evitare deadlock o scritture concorrenti sul file.
        with open(CATALOG_FILE, 'w') as f:
            json.dump(self.catalog, f, indent=4)
    def _cleanup_loop(self):
        # Thread che si attiva ciclicamente
        while True:
            time.sleep(self.cleanup_time // 2)
            current_time = time.time()
            with self.lock:
                cleaned = False
                for category in ['devices', 'services']:
                    to_delete = []
                    for item_id, info in self.catalog[category].items():
                        # Rimuovere le entry più vecchie del tempo di espirazione
                        if current_time - info.get('insert_timestamp', 0) > self.cleanup_time:
                            to_delete.append(item_id)     
                    for item_id in to_delete:
                        del self.catalog[category][item_id]
                        cleaned = True                       
                if cleaned:
                    print(f"[{time.strftime('%X')}] CLEANUP Removed record from catalog")
                    # Il salvataggio ora è protetto dal blocco 'with self.lock'
                    self._save_catalog() 
    @cherrypy.tools.json_out()
    def GET(self, *path, **params):
        with self.lock:  
            # Gestisce il recupero delle informazioni
            if not path:
                return self.catalog    
            category = path[0]
            if category == 'broker':
                return self.catalog.get('broker', {})
            elif category in ['devices', 'services']:
                if len(path) == 1:
                    return self.catalog[category]
                elif len(path) == 2:
                    item_id = path[1]
                    if item_id in self.catalog[category]:
                        return self.catalog[category][item_id]
                    else:
                        raise cherrypy.HTTPError(404, "Record not found")        
            raise cherrypy.HTTPError(400, "Invalid request")
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *path, **params):
        # Controllo path essenziale per evitare IndexError
        if not path or path[0] not in ['devices', 'services']:
             raise cherrypy.HTTPError(400, "Invalid category. Use /devices or /services")
        category = path[0] 
        data = cherrypy.request.json
        item_id = data.get('id') 
        if not item_id:
            raise cherrypy.HTTPError(400, "Payload must contain an 'id' field")
        with self.lock:
            if item_id in self.catalog[category]:
                # Se ESISTE: aggiorna i dati e fai il refresh del timestamp
                self.catalog[category][item_id] = data
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                message = f"ID {item_id} aggiornato con successo"
            else:
                # Se NON ESISTE: crea un nuovo record
                self.catalog[category][item_id] = data
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                message = f"Nuovo ID {item_id} registrato con successo"
            self._save_catalog()
        return {"status": "success", "message": message}
    @cherrypy.tools.json_out()
    def PUT(self, *path, **params):
        # Metodo per l'aggiornamento (refresh) del timestamp
        if len(path) != 2 or path[0] not in ['devices', 'services']:
            raise cherrypy.HTTPError(400, "Usa la sintassi PUT /devices/{id} o /services/{id} per il refresh")
        category = path[0]
        item_id = path[1] 
        with self.lock:
            # Verifichiamo che il nodo sia ancora nel catalogo
            if item_id in self.catalog[category]:
                # Refresh della registrazione
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                # Persistenza
                self._save_catalog()
                return {"status": "success", "message": f"Refresh di {item_id} effettuato con successo."}
            else:
                raise cherrypy.HTTPError(404, f"{item_id} non trovato o scaduto. Necessaria nuova registrazione via POST.")