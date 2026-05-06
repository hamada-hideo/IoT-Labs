import cherrypy
import json
import time
from Globals import *

class SmartHomeActuators(object):
    exposed = True
    
    def __init__(self):
        # rooms is a dict: { room_name: { device_id: device_dict } }
        self.rooms = INITIAL_ACTUATORS_STATE
        self._counter = 0  # global device-ID counter

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _parse_senml(self,raw):
        
        try: 
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise cherrypy.HTTPError(400, "Invalid JSON can't be parsed")
        if not isinstance(data,list) or len(data) ==  0:
            raise cherrypy.HTTPError(422, "Received object is not a list")
        record = data[0]
        if not isinstance(record,dict):
            raise cherrypy.HTTPError(422,"Instances of list aren't dicts")
        
        if "n" not in record:
            raise cherrypy.HTTPError(422, "Received object is not valid SenML")

        return record
        
        

    def _validate_for_device(self, record,device_type):
       
       
        if device_type == "thermostat":
            if "v" not in record:
                return False
            if not isinstance(record["v"], (int, float)):
                return False
            if record["v"] < 10 or record["v"] > 30:
                return False
            return True

        elif device_type == "lights":
            if "vb" not in record:
                return False
            if not isinstance(record["vb"], bool):   # rejects 0/1 integers
                return False
            return True
        
        elif device_type == "blinds":
            if "v" not in record:
                return False
            if not isinstance(record["v"], (int, float)):
                return False
            if record["v"] < 0 or record["v"] > 100:
                return False
            return True
 
        else:
            return False #unknown device type  

        
    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

  #  def GET(self, *uri, **params):
        """
        GET /rooms                        → list all rooms
        GET /rooms/<room>                 → list all devices in a room
        GET /rooms/<room>/<device_id>     → get a specific device
        """
        clean = [seg for seg in uri if seg.strip()]

        # ── CASE 0: /rooms 
        if len(clean) == 0:
            return json.dumps({
                "rooms": list(self.rooms.keys()),
                "total": len(self.rooms)
            }).encode("utf-8")

        # ── CASE 1: /rooms/<room> 
        room = clean[0]
        if room not in self.rooms:
            raise cherrypy.HTTPError(404, json.dumps({"error": f"Room '{room}' not found"}))

        if len(clean) == 1:
            devices = list(self.rooms[room].values())
            return json.dumps({
                "room": room,
                "devices": devices,
                "total": len(devices)
            }).encode("utf-8")

        # ── CASE 2: /rooms/<room>/<device_id> 
        if len(clean) == 2:
            device_id = clean[1]
            if device_id not in self.rooms[room]:
                raise cherrypy.HTTPError(
                    404,
                    json.dumps({"error": f"Device '{device_id}' not found in room '{room}'"})
                )
            return json.dumps(self.rooms[room][device_id]).encode("utf-8")

        # ── CASE ERROR: too many segments 
        raise cherrypy.HTTPError(400, "URI format: /rooms[/<room>[/<device_id>]]")


    #--- PUT -----
    def PUT(self,*uri,**params):
        """
        Docstring for PUT
        /rooms/<room>/<device_id>/   
        """
        clean = [seg for seg in uri if seg.strip()]

        #Check if uri is formatted correctly 
        if len(clean) != 2:
            raise cherrypy.HTTPError(400, "URI format:/rooms/<room>/<device_id>/<val>")
    
        #loads the request body and checks for valid SenML
        record = self._parse_senml(cherrypy.request.body.read())
    
        room, device_id = clean[0], clean[1]

        #Check if room exists and device exists 
        if room not in self.rooms:
            raise cherrypy.HTTPError(404, "Room not found");
        if device_id not in self.rooms[room]:
            raise cherrypy.HTTPError(404, "Device not found");

        # Validate device type 
        if not self._validate_for_device(record,self.rooms[room][device_id]["v"]):
            raise cherrypy.HTTPError(400, "Value is out of range")

        new_state = {}

        if "vb" in record:
            new_state["vb"] = record["vb"]
        else:
            new_state["v"] = record["v"]
        if "u" in record:
            new_state["u"] = record["u"]
        new_state["t"] = time.time()   # timestamp of last command
 
        self.rooms[room][device_id] = new_state

        # ── Return updated state as a SenML pack (200 OK)
        response_record = {
            "bn": f"urn:dev:room:{room}:{device_id}:",
            "n":  record.get("n", device_id),
            "t":  new_state["t"]
        }
        if "vb" in new_state:
            response_record["vb"] = new_state["vb"]
        else:
            response_record["v"] = new_state["v"]
        if "u" in new_state:
            response_record["u"] = new_state["u"]
 
        return json.dumps([response_record]).encode("utf-8")


 

            





    #--------------