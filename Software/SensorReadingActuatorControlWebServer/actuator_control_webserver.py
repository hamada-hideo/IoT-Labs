import cherrypy
import json
import time
import requests
import threading
import os
import SenMLUtils as SenML
from Catalog.catalog_client import *

DIR = os.path.dirname(os.path.abspath(__file__))

class ActuatorControlWebServer:
    exposed = True
    
    def __init__(self, ip, port, endpoint):
        self.config_file = os.path.join(DIR, "actuators_config.json")
        self.state_file = os.path.join(DIR, "actuators_state.json")
        self._load_data()
        self.lock = threading.Lock()

        self.devices_list = self._build_devices_list()

        self.ip = ip
        self.port = port
        self.endpoint = endpoint
        self.id = "ActuatorControlWebServer"
        self.logger_id = "LoggerWebServer"

        self.data = {
            "id": self.id,
            "description": "Service that forwards commands to smart home actuators",
            "rest": {
                "url": f"http://{self.ip}:{self.port}/{self.endpoint}",
                "method": ["GET", "POST"]
            },
            "resources": self._build_resource_list()
        }
        self.registered = False

        self.cc = CatalogClient()

        threading.Thread(target=self._try_register_refresh_loop, daemon=True).start()

        self.logger_url_valid = False
        
        threading.Thread(target=self._try_get_logger_url, daemon=True).start()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_data(self):
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

    def _try_register_refresh_loop(self):
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
        while True:
            time.sleep(self.cc.loop_time)
            res = self.cc.get_service(self.logger_id)
            if res:
                url = res["rest"]["url"]
                self.logger_url = url
                self.logger_url_valid = True
                break

    def _build_devices_list(self):
        res = []
        for room in self.state:
            for actuator in self.state[room]:
                res.append({
                    "device": {
                        "id": f"{room}-{actuator}",
                        "description": f"{actuator} located in room {room}",
                        "resources": {
                            "type": actuator,
                            "unit": self.rules[self.state[room][actuator]["type"]]["unit"],
                            "min": self.rules[self.state[room][actuator]["type"]]["low"],
                            "max": self.rules[self.state[room][actuator]["type"]]["high"]
                        }
                    },
                    "registered": False
                })
        return res
    
    def _build_resource_list(self):
        res = dict()
        for room in self.state:
            res[room] = [a for a in self.state[room]]
        return res

    def _get_room_id_device_id(self, senml_name):
        segments = senml_name.strip().split("/")
        if len(segments) != 3 or segments[0] != "smart_home" or segments[1] not in self.state or segments[2] not in self.state[segments[1]]:
            raise cherrypy.HTTPError(422, "Wrong event name")
        _, room_id, device_id = segments
        return room_id, device_id

    def _validate_for_device(self, record):
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
        room_id, device_id = self._get_room_id_device_id(command[SenML.NAME_KEY])
        # Attenzione: responsabilità del lock al chiamante
        self.state[room_id][device_id]["v"] = command[SenML.VALUE_KEY]
        self.state[room_id][device_id]["t"] = time.time()
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=4)

    def _process_SenML(self, senml):
        # Usa la funzione dal tuo modulo SenMLUtils
        flat_events = SenML.flatten_senml(senml)
        
        cnt = 0
        for event in flat_events:
            if not self._validate_for_device(event):
                raise cherrypy.HTTPError(400, "SenML content invalid")
            self._actuate(event)
            cnt += 1
        
        return cnt
        
    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def GET(self, *uri, **params):
        """
        GET /actuators                        → list all devices
        GET /actuators/<room>                 → list all devices in a room
        GET /actuators/<room>/<device_id>     → get a specific device
        """

        if len(params) > 0:
            raise cherrypy.HTTPError(400, f"Unknown parameters: {[k for k in params.keys()]}")
        
        clean = [seg for seg in uri if seg.strip()]

        # ── CASE 0: /actuators 
        if len(clean) == 0:
            return json.dumps(self._get_all()).encode("utf-8")

        # ── CASE 1: /actuators/<room> 
        room_id = clean[0]
        if room_id not in self.state:
            raise cherrypy.HTTPError(404, json.dumps({"error": f"Room '{room_id}' not found"}))

        if len(clean) == 1:
            return json.dumps(self._get_by_room(room_id)).encode("utf-8")

        # ── CASE 2: /actuators/<room>/<device_id> 
        if len(clean) == 2:
            device_id = clean[1]
            if device_id not in self.state[room_id]:
                raise cherrypy.HTTPError(404, json.dumps({"error": f"Device '{device_id}' not found in room '{room_id}'"}))
            return json.dumps(self._get_by_room_and_device(room_id, device_id)).encode("utf-8")


        # ── CASE ERROR: too many segments 
        raise cherrypy.HTTPError(400, "URI format: /actuators[/<room>[/<device_id>]]")


    #--- POST -----
    def POST(self,*uri,**params):
        """
        POST /actuators with SenML payload
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
                threading.Thread(target=self.cc.try_get_url, args = ("LoggerWebServer", self._on_logger_url), daemon=True).start()

        return json.dumps({
            "message": f"Executed {cnt} commands"
        }).encode("utf-8")
