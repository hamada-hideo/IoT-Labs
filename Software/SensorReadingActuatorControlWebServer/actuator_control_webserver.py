# EXERCISE: Exercise 06 / Exercise 09 Extension - Actuator REST Controller
# ACTOR: ActuatorControlWebServer (Central Actuator Orchestrator)
# DESCRIPTION: Manages the internal execution states of smart home actuators.
#              Exposes a hierarchical REST API, interfaces with an internal MQTT
#              bridge framework, and forwards processed operation footprints 
#              downstream to the LoggerWebServer using synchronous HTTP requests.

# SECTION 1: SYSTEM ENVIRONMENT & CROSS-PACKAGE IMPORT LOGIC
import cherrypy
import json
import time
import requests
import threading
import os
import sys
import SenMLUtils as SenML
from Catalog.catalog_client import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from SensorReadingActuatorControlWebServer.mqtt_actuators_bridge import *

DIR = os.path.dirname(os.path.abspath(__file__))

# SECTION 2: CLASS INITIALIZATION & SUBSYSTEM COUPLING
class ActuatorControlWebServer:
    exposed = True
    
    def __init__(self, ip, port, endpoint):
        """
        Constructor method. Validates internal rule configuration sets, generates
        sub-resource representations, initializes the MQTT bridge, and binds Catalog routines.
        """
        self.config_file = os.path.join(DIR, "actuators_config.json")
        self.state_file = os.path.join(DIR, "actuators_state.json")
        self._load_data()
        self.lock = threading.Lock()

        self.ip = ip
        self.port = port
        self.endpoint = endpoint
        self.id = "ActuatorControlWebServer"
        self.logger_id = "LoggerWebServer"

        self.devices_list = self._build_devices_list()

        self.data = {
            "id": self.id,
            "description": "Service that forwards commands to smart home actuators",
            "rest": {
                "url": f"http://{self.ip}:{self.port}/{self.endpoint}"
            },
            "resources": self._build_resource_list()
        }
        self.registered = False

        self.cc = CatalogClient()

        threading.Thread(target=self._try_register_refresh_loop, daemon=True).start()

        self.logger_url_valid = False
        
        threading.Thread(target=self._try_get_logger_url, daemon=True).start()

        self.mqtt_bridge = MQTTActuatorsControlBridge(self)
        threading.Thread(target=self.mqtt_bridge.run, daemon=True).start()
    # SECTION 3: SYSTEM VALIDATION & FILE SYSTEM PERSISTENCE METHODS
    def _load_data(self):
        """
        Internal private helper. Parses validation configuration parameters and synchronizes 
        the active operational state matrix with stored JSON file system values.
        """
        with open(self.config_file, "r") as f:
            data = json.load(f)
            self.rules = data["rules"]
            config_state = data["initial_state"]
        to_overwrite = False
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    self.state = json.load(f)
                if not self._validate_state(config_state):
                    to_overwrite = True
            except json.JSONDecodeError:
                to_overwrite = True
        else:
            to_overwrite = True
        if to_overwrite:
            self.state = config_state
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=4)

    def _validate_state(self, reference):
        """
        Ensures the local database architecture accurately mimics configured boundaries
        by verifying metric ranges, properties, units, and structural integrity.
        """
        for room in self.state:
            if room not in reference:
                return False
        for room in reference:
            if room not in self.state:
                return False
        for room in self.state:
            for device in self.state[room]:
                if device not in reference[room]:
                    return False
            for device in reference[room]:
                if device not in self.state[room]:
                    return False
        for room in self.state:
            for device in self.state[room]:
                if self.state[room][device]["type"] not in self.rules:
                    return False
                if self.state[room][device]["u"] != self.rules[self.state[room][device]["type"]]["unit"]:
                    return False
                if self.rules[self.state[room][device]["type"]]["low"] is not None and self.state[room][device]["v"] < self.rules[self.state[room][device]["type"]]["low"]:
                    return False
                if self.rules[self.state[room][device]["type"]]["high"] is not None and self.state[room][device]["v"] > self.rules[self.state[room][device]["type"]]["high"]:
                    return False
        return True
    # SECTION 4: BACKGROUND DISCOVERY & RESOURCE GENERATION ROUTINES
    def _try_register_refresh_loop(self):
        """
        Maintains registration states inside the central Catalog database for both
        the main controller service and each standalone physical actuator endpoint.
        """
        while True:
            time.sleep(self.cc.loop_time)
            if not self.registered:
                if self.cc.register_service(self.data):
                    self.registered = True
            else:
                if not self.cc.refresh_service(self.id):
                    self.registered = False
            for i in range(len(self.devices_list)):
                if not self.devices_list[i]["registered"]:
                    if self.cc.register_device(self.devices_list[i]["device"]):
                        self.devices_list[i]["registered"] = True
                else:
                    if not self.cc.refresh_device(self.devices_list[i]["device"]["id"]):
                        self.devices_list[i]["registered"] = False

    def _try_get_logger_url(self):
        """
        Polls the Catalog registry endpoint until the core central historical database service
        is successfully identified, resolving its target connectivity URL dynamically.
        """
        while True:
            time.sleep(self.cc.loop_time)
            res = self.cc.get_service(self.logger_id)
            if res:
                url = res["rest"]["url"]
                self.logger_url = url
                self.logger_url_valid = True
                break

    def _build_devices_list(self):
        """
        Iterates over state maps to build and populate comprehensive individual 
        profiles for every active physical actuator, registering communication channels.
        """
        res = []
        for room in self.state:
            for actuator in self.state[room]:
                command_topic = f"/tiot/group12/smart_home/{room}/{actuator}/config"
                res.append({
                    "device": {
                        "id": f"{room}/{actuator}",
                        "description": f"{actuator} located in room {room}",
                        "resources": {
                            "type": self.state[room][actuator]["type"],
                            "unit": self.rules[self.state[room][actuator]["type"]]["unit"],
                            "min": self.rules[self.state[room][actuator]["type"]]["low"],
                            "max": self.rules[self.state[room][actuator]["type"]]["high"]
                        },
                        "mqtt": {
                            "command_topic": command_topic,
                            "feedback_topic": f"/tiot/group12/smart_home/{room}/{actuator}/state",
                            "logger_topic": command_topic
                        },
                        "rest": {
                            "url": f"http://{self.ip}:{self.port}/{self.endpoint}/{room}/{actuator}"
                        }
                    },
                    "registered": False
                })
        return res
    
    def _build_resource_list(self):
        """Builds a condensed structure mapping rooms to their respective hardware tokens."""
        res = dict()
        for room in self.state:
            res[room] = [a for a in self.state[room]]
        return res
    # SECTION 5: DOMAIN SPECIFIC INTERNAL ACTUATION LOGIC
    def _get_room_id_device_id(self, senml_name):
        """Extracts spatial context configurations by evaluating SenML name tokens."""
        segments = senml_name.strip().split("/")
        if len(segments) != 3 or segments[0] != "smart_home" or segments[1] not in self.state or segments[2] not in self.state[segments[1]]:
            raise cherrypy.HTTPError(422, "Wrong event name")
        _, room_id, device_id = segments
        return room_id, device_id

    def _validate_for_device(self, record):
        """Checks incoming event metrics against physical unit definitions and boundary rules."""
        room_id, device_id = self._get_room_id_device_id(record[SenML.NAME_KEY])
        device_type = self.state[room_id][device_id]["type"]

        if device_type not in self.rules:
            return False
        
        if self.rules[device_type]["low"] != None and record[SenML.VALUE_KEY] < self.rules[device_type]["low"]:
            return False
        if self.rules[device_type]["high"] != None and record[SenML.VALUE_KEY] > self.rules[device_type]["high"]:
            return False
        if record[SenML.UNIT_KEY] != self.rules[device_type]["unit"]:
            return False
        
        return True

    def _get_all(self):
        """Thread-safe state converter. Bundles full memory arrays into formal global SenML outputs."""
        with self.lock:
            return SenML.build_array_dict(
                [SenML.build_event_dict(
                    f"{room_id}/{device_id}",
                    self.state[room_id][device_id]["u"],
                    self.state[room_id][device_id]["v"],
                    self.state[room_id][device_id]["t"],
                ) for room_id in self.state for device_id in self.state[room_id]],
                "smart_home/"
            )

    def _get_by_room(self, room_id):
        """Thread-safe state converter. Isolates individual room entries into localized SenML blocks."""
        with self.lock:
            room = self.state[room_id]
            return SenML.build_array_dict(
                [SenML.build_event_dict(
                    device_id,
                    room[device_id]["u"],
                    room[device_id]["v"],
                    room[device_id]["t"]
                ) for device_id in room.keys()],
                f"smart_home/{room_id}/"
            )

    def _get_by_room_and_device(self, room_id, device_id):
        """Thread-safe data retrieval engine for a single, target hardware asset component."""
        with self.lock:
            room = self.state[room_id]
            device = room[device_id]
            return SenML.build_array_dict(
                [SenML.build_event_dict(
                    f"smart_home/{room_id}/{device_id}",
                    device["u"],
                    device["v"],
                    device["t"]
                )]
            )

    def _actuate(self, command):
        """Modifies volatile memory states and saves changes to disk."""
        room_id, device_id = self._get_room_id_device_id(command[SenML.NAME_KEY])
        self.state[room_id][device_id]["v"] = command[SenML.VALUE_KEY]
        self.state[room_id][device_id]["t"] = time.time()
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=4)

    def _process_SenML(self, senml, room = None, id = None):
        """Flattens input payloads, validates each entry, and executes actuation commands."""
        flat_events = SenML.flatten_senml(senml)
        
        cnt = 0
        for event in flat_events:
            if room and id:
                event_room, event_id = self._get_room_id_device_id(event[SenML.NAME_KEY])
                if room != event_room or id != event_id:
                    continue
            if not self._validate_for_device(event):
                raise cherrypy.HTTPError(400, "SenML content invalid")
            self._actuate(event)
            cnt += 1
        
        return cnt
        # SECTION 6: HTTP REST ENDPOINTS (GET & POST CAPABILITIES)
    def GET(self, *uri, **params):
        """
        Handles HTTP GET requests. Parses routing levels dynamically to output global telemetry,
        room arrays, or single device snapshots.
        """
        if len(params) > 0:
            raise cherrypy.HTTPError(400, f"Unknown parameters: {[k for k in params.keys()]}")
        
        clean = [seg for seg in uri if seg.strip()]

        if len(clean) == 0:
            return json.dumps(self._get_all()).encode("utf-8")

        room_id = clean[0]
        if room_id not in self.state:
            raise cherrypy.HTTPError(404, json.dumps({"error": f"Room '{room_id}' not found"}))

        if len(clean) == 1:
            return json.dumps(self._get_by_room(room_id)).encode("utf-8")

        if len(clean) == 2:
            device_id = clean[1]
            if device_id not in self.state[room_id]:
                raise cherrypy.HTTPError(404, json.dumps({"error": f"Device '{device_id}' not found in room '{room_id}'"}))
            return json.dumps(self._get_by_room_and_device(room_id, device_id)).encode("utf-8")

        raise cherrypy.HTTPError(400, "URI format: /actuators[/<room>[/<device_id>]]")


    def POST(self,*uri,**params):
        """
        Handles HTTP POST requests. Decodes validation commands, updates states, 
        and sends synchronous HTTP data logs downstream to the central Logger microservice.
        """
        if len(uri) > 0:
            raise cherrypy.HTTPError(404, "URI too specific")
        if len(params) > 0:
            raise cherrypy.HTTPError(400, f"Unknown parameters: {[k for k in params.keys()]}")
        
        try:
            data = json.loads(cherrypy.request.body.read())
        except json.JSONDecodeError:
            raise cherrypy.HTTPError(422, "Request body must be valid JSON")

        if not SenML.validate_SenML(data):
            raise cherrypy.HTTPError(422, f"Wrong SenML format: {data}")
        
        cnt = self._process_SenML(data)

        if self.logger_url_valid:
            try:
                # Effettuiamo una POST locale all'endpoint del logger (es. porta 8080)
                response = requests.post(self.logger_url, json=data, timeout=2)
                if response.status_code != 200:
                    print(f"Attenzione: Impossibile salvare il log. Risposta del server: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                # Se il logger è spento, stampiamo l'errore su console 
                # ma non facciamo crashare il server attuatori
                print(f"Attenzione: Impossibile salvare il log. Errore: {e}")
                self.logger_url_valid = False
                threading.Thread(target=self._try_get_logger_url, args = ("LoggerWebServer", self._on_logger_url), daemon=True).start()
        else:
            print(f"Attenzione: Impossibile salvare il log. Non è stato possibile ottenere l'url del logger.")

        return json.dumps({
            "message": f"Executed {cnt} commands"
        }).encode("utf-8")
