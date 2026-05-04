import cherrypy
import json
import time


class SmartHomeActuators(object):
    exposed = True

    def __init__(self):
        # rooms is a dict: { room_name: { device_id: device_dict } }
        self.rooms = {}
        self._counter = 0  # global device-ID counter

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _next_id(self):
        """Generate a unique device ID like d001, d002, …"""
        self._counter += 1
        return f"d{self._counter:03d}"

    def _validate_device(self, data):
        """A device payload must contain at least 'name' and 'type'."""
        return isinstance(data, dict) and "name" in data and "type" in data

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def GET(self, *uri, **params):
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

    # ------------------------------------------------------------------
    # POST
    # ------------------------------------------------------------------

    def POST(self, *uri, **params):
        """
        POST /rooms/<room>   body: {"name": ..., "type": ..., "value": ..., "unit": ...}
                             
                       -> add a device; room is auto-created if it does not exist
        """
        clean = [seg for seg in uri if seg.strip()]

        if len(clean) != 1:
            raise cherrypy.HTTPError(400, "URI format: /rooms/<room>")

        room = clean[0]

        # Read and validate body
        try:
            data = json.loads(cherrypy.request.body.read())
        except json.JSONDecodeError:
            raise cherrypy.HTTPError(400, "Request body must be valid JSON")

        if not self._validate_device(data):
            raise cherrypy.HTTPError(
                400,
                json.dumps({"error": "Missing required fields: 'name' and 'type'"})
            )

        # Auto-create room on first POST
        if room not in self.rooms:
            self.rooms[room] = {}

        device_id = self._next_id()
        self.rooms[room][device_id] = {
            "device_id": device_id,
            "room": room,
            "name": data["name"],
            "type": data["type"],
            "value": data.get("value"),
            "unit": data.get("unit"),
            "added_at": time.time()
        }

        cherrypy.response.status = 201
        return json.dumps({
            "message": "Device added",
            "device_id": device_id,
            "room": room
        }).encode("utf-8")

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def DELETE(self, *uri, **params):
        """
        DELETE /rooms/<room>/<device_id>  -> remove a specific device
        """
        clean = [seg for seg in uri if seg.strip()]

        if len(clean) != 2:
            raise cherrypy.HTTPError(400, "URI format: /rooms/<room>/<device_id>")

        room, device_id = clean[0], clean[1]

        if room not in self.rooms:
            raise cherrypy.HTTPError(404, json.dumps({"error": f"Room '{room}' not found"}))

        if device_id not in self.rooms[room]:
            raise cherrypy.HTTPError(
                404,
                json.dumps({"error": f"Device '{device_id}' not found in room '{room}'"})
            )

        removed = self.rooms[room].pop(device_id)
        return json.dumps({
            "message": f"Device '{device_id}' removed from room '{room}'",
            "removed_device": removed
        }).encode("utf-8")

