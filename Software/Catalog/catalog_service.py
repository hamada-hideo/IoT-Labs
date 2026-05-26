import cherrypy
import json
import threading
import time
import os
from Catalog.catalog_info import *

CATALOG_FILE = 'catalog.json'

class Catalog(object):
    exposed = True

    def __init__(self):
        #Utilizzo un Lock per evitare race conditions durante lettura/scrittura
        self.lock = threading.Lock()
        #struttura base del catalogo che contiene le info del broker al livello root
        self.catalog = {
            "broker":{"ip": "broker.hivemq.com","port":1883},
            "devices":{},
            "services":{}
        }
        #Ricarica il catalogo dal file JSON all'avvio
        self._load_catalog()
        #avvia il thread in background per la pulizia dei record obsoleti
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
    
    def _load_catalog(self):
        with self.lock:
            if os.path.exists(CATALOG_FILE):
                try:
                    with open(CATALOG_FILE,'r') as f:
                        self.catalog = json.load(f)
                except json.JSONDecodeError:
                    self._save_catalog_unsafe()
            else:
                self._save_catalog_unsafe()
    
    def _save_catalog_unsafe(self):
        #salva lo stato su file per la persistenza
        with open(CATALOG_FILE, 'w') as f:
            json.dump(self.catalog, f, indent=4)
    
    def _cleanup_loop(self):
        #Thread che si attiva ogni 60 secondi
        while True:
            time.sleep(CATALOG_EXPIRATION_TIME // 2)
            current_time = time.time()
            with self.lock:
                cleaned = False
                for category in ['devices','services']:
                    to_delete = []
                    for item_id, info in self.catalog[category].items():
                        #Rimuovere le entry più vecchie di 120 secondi
                        if current_time -info.get('insert_timestamp', 0) > CATALOG_EXPIRATION_TIME:
                            to_delete.append(item_id)
                    for item_id in to_delete:
                        del self.catalog[category][item_id]
                        cleaned = True
            if cleaned:
                print(f"[{time.strftime('%X')}] CLEANUP Removed record from catalog")
                self._save_catalog_unsafe()
    
    @cherrypy.tools.json_out()
    def GET(self, *path, **params):
        with self.lock:  
            #Gestisce il recupero delle informazioni del broker, dispositivi o servizi
            if not path:
                return self.catalog
            category = path[0]
            if category == 'broker':
                return self.catalog.get('broker',{})
            elif category in ['devices','services']:
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
        #Crea o aggiorna un dispositivo o un servizio
        if not path or path[0] not in ['devices','services']:
            raise cherrypy.HTTPError(400, "Use /devices or /services")
        category = path[0]
        data = cherrypy.request.json
        item_id = data.get('id')
        if not item_id:
            raise cherrypy.HTTPError(400, " ID not found")
        with self.lock:
            if item_id in self.catalog[category]:
                raise cherrypy.HTTPError(400)
                # È un refresh: aggiorniamo solo il timestamp
            data['insert_timestamp'] = time.time()
            self.catalog[category][item_id] = data
            self._save_catalog_unsafe()
        return{"staus":"success","messagge":f"Nuovo {category[:-1]}({item_id}) registred"}
    
    @cherrypy.tools.json_out()
    def PUT(self, *path, **params):
    # IL METODO PUT È USATO PER IL REFRESH DEL TIMESTAMP (AGGIORNAMENTO RISORSA)
    
    # Un refresh corretto in REST avviene puntando alla risorsa specifica: /devices/<id>
        if len(path) != 2 or path[0] not in ['devices', 'services']:
            raise cherrypy.HTTPError(400, "Usa la sintassi PUT /devices/{id} o /services/{id} per il refresh")
    
        category = path[0]
        item_id = path[1] # Questo è l'ID ricavato dall'URL
    
        with self.lock:
        # Verifichiamo che il nodo sia effettivamente ancora vivo nel catalogo (non cancellato dal cleanup)
            if item_id in self.catalog[category]:
            
            # Aggiorniamo ESCLUSIVAMENTE il timestamp (refresh della registrazione)
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
            
            # OPZIONALE: se vuoi permettere al device di aggiornare anche altri parametri nel payload (es. risorse list)
            # de-commenta le due righe successive e aggiungi @cherrypy.tools.json_in() al decoratore sopra.
            # if cherrypy.request.json:
            #     self.catalog[category][item_id].update(cherrypy.request.json)

            # Persistenza del salvataggio
                self._save_catalog_unsafe()
                return {"status": "success", "message": f"Refresh di {item_id} effettuato con successo."}
            else:
            # Se provano a fare refresh di un device già scaduto/inesistente
                raise cherrypy.HTTPError(404, f"{item_id} non trovato o scaduto. Necessaria nuova registrazione via POST.")
