import cherrypy
import json
import time
from Globals import *
import SenMLUtils as SenML

class ActuatorControlWebServer:
    exposed = True
    
    def __init__(self):
        # rooms is a dict: { room_name: { device_id: device_dict } }
        self.rooms = INITIAL_ACTUATORS_STATE

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_room_id_device_id(self, senml_name):
        segments = senml_name.strip().split("/")
        if len(segments) != 3 or segments[0] != "smart_home" or segments[1] not in self.rooms.keys() or segments[2] not in self.rooms[segments[1]].keys():
            raise cherrypy.HTTPError(422, "Wrong event name")
        _, room_id, device_id = segments
        return room_id, device_id

    def _validate_for_device(self, record):
        _, device_type = self._get_room_id_device_id(record[SenML.NAME_KEY])

        if device_type not in ACTUATOR_RULES.keys():
            return False
        
        if not isinstance(record[SenML.VALUE_KEY], ACTUATOR_RULES[device_type]["type"]):
            return False
        if ACTUATOR_RULES[device_type]["low"] != None and record[SenML.VALUE_KEY] < ACTUATOR_RULES[device_type]["low"]:
            return False
        if ACTUATOR_RULES[device_type]["high"] != None and record[SenML.VALUE_KEY] > ACTUATOR_RULES[device_type]["high"]:
            return False
        if record[SenML.UNIT_KEY] != ACTUATOR_RULES[device_type]["unit"]:
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

        return json.dumps({
            "message": f"Executed {cnt} commands"
        }).encode("utf-8")
