EXERCISE 7

# --- Section 1: Library Imports and Path Configuration ---
# Standard libraries for web services (cherrypy), data (json), and concurrency (threading).
# The system path is updated to allow importing the MQTT bridge from the Catalog package.

import cherrypy
import json
import threading
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Import the MQTT bridge to enable the dual interface (REST + MQTT)

from Catalog.mqtt_catalog_bridge import *

DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_FILE = os.path.join(DIR, 'catalog.json')

# --- Section 2: Catalog Class Initialization and Persistence ---
# The constructor loads the existing catalog from 'catalog.json' on startup.
# It initializes a threading lock to prevent race conditions during file access
# and starts a background thread for automatic maintenance.

class Catalog(object):
    exposed = True

    def __init__(self):
        """
        Constructor method. Loads the network configuration, initializes the in-memory 
        catalog structure, recovers persisted data, and starts background threads.
        """
        # Load core settings (expiration time, MQTT broker details) from network config file
        self.config_file = os.path.join(DIR, "network_config.json")
        with open(self.config_file, "r") as f:
            data = json.load(f)
            
        self.cleanup_time = data["expiration_time"]
        self.broker = data["mqtt"]["broker"]

        # Thread lock instantiation to prevent race conditions during concurrent data access
        self.lock = threading.Lock()

        # Initialize default structure for in-memory storage
        self.catalog = {
            "broker": self.broker,
            "devices": {},
            "services": {}
        }

        # Load previously saved catalog data from disk if it exists
        self._load_catalog()
        # Start the background maintenance thread to purge stale registrations periodically
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

#        Initialize and run the MQTT bridge, passing this catalog instance as a reference
        
        self.mqtt_bridge = MQTTCatalogBridge(self)
        threading.Thread(target=self.mqtt_bridge.run, daemon=True).start()

# SECTION 3: INTERNAL PERSISTENCE & MAINTENANCE METHODS
    
    def _load_catalog(self):

        """
        Internal helper method to load the persisted catalog file from disk on startup.
        Ensures essential keys ('devices', 'services') exist and updates broker info.
        """
        
        with self.lock:
            if os.path.exists(CATALOG_FILE):
                try:
                    with open(CATALOG_FILE, 'r') as f:
                        self.catalog = json.load(f)  
                        #Ensure consistency in structure by re-initializing missing sections
                    if 'devices' not in self.catalog:
                        self.catalog['devices'] = {}
                    if 'services' not in self.catalog:
                        self.catalog['services'] = {}
                    # Synchronize the broker URL with the latest network configuration
                    self.catalog['broker'] = self.broker
                    
                except json.JSONDecodeError:
                    self._save_catalog() 
            else:
                # If file is corrupted, re-initialize with a fresh save
                self._save_catalog()

    def _save_catalog(self):
        """
        Internal helper method to dump the current state of the in-memory catalog 
        into a formatted JSON file.
        """
        with open(CATALOG_FILE, 'w') as f:
            json.dump(self.catalog, f, indent=4)

    def _cleanup_loop(self):
        """
        Infinite loop running as a background thread to remove stale device and service 
        registrations whose timestamps have exceeded the designated cleanup lifespan.
        """
        while True:
            time.sleep(self.cleanup_time // 2)
            current_time = time.time()
            with self.lock:
                cleaned = False
                for category in ['devices', 'services']:
                    to_delete = []
                    # Track registrations that have expired
                    for item_id, info in self.catalog[category].items():
                        if current_time - info.get('insert_timestamp', 0) > self.cleanup_time:
                            to_delete.append(item_id) 
                            # Remove identified stale entries from the dictionary
                    for item_id in to_delete:
                        del self.catalog[category][item_id]
                        cleaned = True 
                        # Persist changes and log the operation if records were deleted
                if cleaned:
                    print(f"[{time.strftime('%X')}] CLEANUP Removed record from catalog")
                    self._save_catalog() 

    # SECTION 4: REST ENDPOINTS (HTTP METHODS)
    @cherrypy.tools.json_out()
    def GET(self, *path, **params):
        """
        Handles HTTP GET requests. Retrieves the full catalog, broker details, 
        entire categories, or single records specified by their resource ID.
        """
        with self.lock:  
            if not path:
                return self.catalog    
            category = path[0]
            # Handle broker retrieval endpoint: GET /broker
            if category == 'broker':
                return self.catalog.get('broker', {})
                # Handle devices and services endpoints: GET /devices or GET /services
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
            # Raise Bad Request error if the endpoint is invalid
            raise cherrypy.HTTPError(400, "Invalid request")

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *path, **params):

"""
        Handles HTTP POST requests. Registers a brand new device/service or updates 
        an entire payload entry based on the identifier provided within the JSON payload.
        """
        
        if not path or path[0] not in ['devices', 'services']:
             raise cherrypy.HTTPError(400, "Invalid category. Use /devices or /services")
        category = path[0] 
        data = cherrypy.request.json
        item_id = data.get('id') 
        if not item_id:
            raise cherrypy.HTTPError(400, "Payload must contain an 'id' field")
        with self.lock:
            # Check if the registration is an update or a fresh addition
            if item_id in self.catalog[category]:
                self.catalog[category][item_id] = data
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                message = f"ID {item_id} aggiornato con successo"
            else:
                self.catalog[category][item_id] = data
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                message = f"Nuovo ID {item_id} registrato con successo"
             # Save the updated dictionary to the file system   
            self._save_catalog()
        return {"status": "success", "message": message}

    @cherrypy.tools.json_out()
    def PUT(self, *path, **params):
        """
        Handles HTTP PUT requests. Used as a keep-alive signal to refresh 
        the insertion timestamp of existing records to keep them from expiring.
        """
        # --- FIX: Accetta percorsi lunghi e ricuce l'ID ---
        if len(path) < 2 or path[0] not in ['devices', 'services']:
            raise cherrypy.HTTPError(400, "Usa la sintassi PUT /devices/{id} o /services/{id} per il refresh")
        
        category = path[0]
        item_id = "/".join(path[1:]) # Ricuce living_room/thermostat
        
        with self.lock:
            # Refresh entry if present, otherwise reject asking for a new POST registration
            if item_id in self.catalog[category]:
                self.catalog[category][item_id]['insert_timestamp'] = time.time()
                self._save_catalog()
                return {"status": "success", "message": f"Refresh di {item_id} effettuato con successo."}
            else:
                raise cherrypy.HTTPError(404, f"{item_id} non trovato o scaduto. Necessaria nuova registrazione via POST.")
