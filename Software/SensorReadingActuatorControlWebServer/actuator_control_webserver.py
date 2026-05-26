import cherrypy
import json
import time
import requests
import threading
import SenMLUtils as SenML
from Catalog.catalog_client import *

class ActuatorControlWebServer:
    exposed = True
    
    def __init__(self, ip, port, endpoint):
        # rooms is a dict: { room_name: { device_id: device_dict } }
        self.rooms = {
            "living_room": {
                "thermostat": {"v": 20.0, "u": "Cel", "t": 0},
                "lights": {"v": False, "u": "bool", "t": 0},
                "blinds": {"v": 0, "u": "%", "t": 0}
            },
            "kitchen": {
                "thermostat": {"v": 20.0, "u": "Cel", "t": 0},
                "lights": {"v": False, "u": "bool", "t": 0},
                "blinds": {"v": 0, "u": "%", "t": 0}
            },
            "bedroom": {
                "thermostat": {"v": 20.0, "u": "Cel", "t": 0},
                "lights": {"v": False, "u": "bool", "t": 0},
                "blinds": {"v": 0, "u": "%", "t": 0}
            }
        }

        self.actuator_rules = {
            "thermostat": {
                "unit": "Cel",
                "low": 10,
                "high": 30,
                "type": (float, int)
            },
            "lights": {
                "unit": "bool",
                "low": None,
                "high": None,
                "type": bool
            },
            "blinds": {
                "unit": "%",
                "low": 0,
                "high": 100,
                "type": (float, int)
            }
        }

        self.ip = ip
        self.port = port
        self.endpoint = endpoint
        self.id = "AcutatorControlWebServer"

        self.cc = CatalogClient()

        self.cc.register_service({
            "id": self.id,
            "description": "Service that forwards commands to smart home actuators",
            "rest": {
                "url": f"http://{self.ip}:{self.port}/{self.endpoint}",
                "method": ["GET", "POST"]
            },
            "resources": self._build_resource_list()
        })

        threading.Thread(target=self.cc.refresh_service_loop, args = (self.id,), daemon=True).start()

        self.logger_url_valid = False
        
        threading.Thread(target=self._try_get_url, args = ("LoggerWebServer",), daemon=True).start()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _try_get_url(self, id):
        while True:
            time.sleep(self.cc.loop_time)
            if not self.logger_url_valid:
                res = self.cc.get_service(id)
                if res:
                    self.logger_url = res["rest"]["url"]
                    self.logger_url_valid = True

    def _build_resource_list(self):
        res = dict()
        for room in self.rooms:
            res[room] = dict()
            for actuator in self.actuator_rules:
                res[room][actuator] = {
                    "type": actuator,
                    "unit": self.actuator_rules[actuator]["unit"],
                    "min": self.actuator_rules[actuator]["low"],
                    "max": self.actuator_rules[actuator]["high"]
                }
        return res

    def _get_room_id_device_id(self, senml_name):
        segments = senml_name.strip().split("/")
        if len(segments) != 3 or segments[0] != "smart_home" or segments[1] not in self.rooms.keys() or segments[2] not in self.rooms[segments[1]].keys():
            raise cherrypy.HTTPError(422, "Wrong event name")
        _, room_id, device_id = segments
        return room_id, device_id

    def _validate_for_device(self, record):
        _, device_type = self._get_room_id_device_id(record[SenML.NAME_KEY])

        if device_type not in self.actuator_rules.keys():
            return False
        
        if not isinstance(record[SenML.VALUE_KEY], self.actuator_rules[device_type]["type"]):
            return False
        if self.actuator_rules[device_type]["low"] != None and record[SenML.VALUE_KEY] < self.actuator_rules[device_type]["low"]:
            return False
        if self.actuator_rules[device_type]["high"] != None and record[SenML.VALUE_KEY] > self.actuator_rules[device_type]["high"]:
            return False
        if record[SenML.UNIT_KEY] != self.actuator_rules[device_type]["unit"]:
            return False
        
        return True

    def _get_all(self):
        return SenML.build_array_dict(
            [SenML.build_event_dict(
                f"{room_id}/{device_id}",
                self.rooms[room_id][device_id]["u"],
                self.rooms[room_id][device_id]["v"],
                self.rooms[room_id][device_id]["t"],
            ) for room_id in self.rooms.keys() for device_id in self.rooms[room_id].keys()],
            "smart_home/"
        )

    def _get_by_room(self, room_id):
        room = self.rooms[room_id]
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
        room = self.rooms[room_id]
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
        self.rooms[room_id][device_id]["v"] = command[SenML.VALUE_KEY]
        self.rooms[room_id][device_id]["t"] = time.time()

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
        GET /actuators                        → list all rooms
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
        if room_id not in self.rooms:
            raise cherrypy.HTTPError(404, json.dumps({"error": f"Room '{room_id}' not found"}))

        if len(clean) == 1:
            return json.dumps(self._get_by_room(room_id)).encode("utf-8")

        # ── CASE 2: /actuators/<room>/<device_id> 
        if len(clean) == 2:
            device_id = clean[1]
            if device_id not in self.rooms[room_id].keys():
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

        try:
            # Effettuiamo una POST locale all'endpoint del logger (es. porta 8080)
            response = requests.post(self.logger_url, json=data, timeout=2)
            if response.status_code != 200:
                print(f"Attenzione: Impossibile salvare il log. Risposta del server: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            # Se il logger è spento, stampiamo l'errore su console 
            # ma non facciamo crashare il server attuatori
            print(f"Attenzione: Impossibile salvare il log. Errore: {e}")

        return json.dumps({
            "message": f"Executed {cnt} commands"
        }).encode("utf-8")
