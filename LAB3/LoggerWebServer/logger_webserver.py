import cherrypy
import json
import time
from Globals import *
import SenMLUtils as SenML

class LoggerWebServer():
    exposed = True

    def __init__(self):
        self.logs = []
        self.id = 0

    def GET(self, *path, **query):
        room = None
        since = None
        before = None
        for key in query.keys():
            if key.strip() not in {"room", "since", "before"}:
                raise cherrypy.HTTPError(400, f"Unknown parameter: {key}")
        if len(path) > 1:
            raise cherrypy.HTTPError(404, "URI too specific")
        if len(path) == 0:
            if "room" in query.keys():
                room = query["room"]
        else:
            if "room" in query.keys() and query["room"] != path[0]:
                raise cherrypy.HTTPError(400, "Path and query parameter conflict for room selection")
            room = path[0]
        if "since" in query.keys():
            try:
                since = float(query["since"])
            except ValueError:
                raise cherrypy.HTTPError(422, "Timestamp must be a float")
        if "before" in query.keys():
            try:
                before = float(query["before"])
            except ValueError:
                raise cherrypy.HTTPError(422, "Timestamp must be a float")
        if room is not None and room not in ROOMS:
            raise cherrypy.HTTPError(404, f"Room {room} not found")
        return json.dumps(self._get_logs_by_room_and_time(room, since, before)).encode("utf-8")

    def POST(self, *path, **query):
        if len(path) > 0:
            raise cherrypy.HTTPError(404, "URI too specific")
        if len(query) > 0:
            raise cherrypy.HTTPError(400, f"Unknown parameters: {[k for k in query.keys()]}")
        ids = []
        try:
            data = json.loads(cherrypy.request.body.read())
        except json.JSONDecodeError:
            raise cherrypy.HTTPError(422, "Request body must be valid JSON")
        if isinstance(data, dict):
            if not SenML.validate_SenML(data):
                raise cherrypy.HTTPError(422, f"Wrong SenML format: {data}")
            id = self._process_SenML(data)
            ids.append(id)
        elif isinstance(data, list):
            for j in data:
                if not SenML.validate_SenML(j):
                    raise cherrypy.HTTPError(422, f"Wrong SenML format: {j}")
                id = self._process_SenML(j)
                ids.append(id)
        else:
            raise cherrypy.HTTPError(400, "Wrong format, expecting a SenML json or an array of SenML json")
        return json.dumps({
            "message": f"{len(ids)} logs added with ids = {ids}",
        }).encode("utf-8")

    def DELETE(self, *path, **query):
        if len(path) > 0:
            raise cherrypy.HTTPError(404, "URI too specific")
        for key in query.keys():
            if key.strip() != "before":
                raise cherrypy.HTTPError(400, f"Unknown parameter: {key}")
        try:
            before = float(query["before"])
        except KeyError:
            raise cherrypy.HTTPError(400, "Missing before parameter")
        except ValueError:
            raise cherrypy.HTTPError(400, "Timestamp must be a float")
        deleted = self._delete_logs_by_time(before)
        return json.dumps({
            "message": f"{len(deleted)} logs deleted with ids = {deleted}"
        }).encode("utf-8")

    def _get_logs_by_room_and_time(self, room = None, since = None, before = None):
        res = []
        for log in self.logs:
            event = log[SenML.EVENTS_KEY][0]

            # Controlla se la stanza è presente nel nome assoluto (bn+n)
            segments = event[SenML.NAME_KEY].strip().split("/")
            if segments[0] != "smart_home" or segments[1] not in ROOMS or segments[2] not in SENSOR_TYPES.keys() or len(segments) > 3:
                raise cherrypy.HTTPError(422, "Wrong event name")
            match_room = (room is None) or (segments[1] == room)
            
            # Controlla il tempo assoluto dell'evento (bt+t)
            match_since = (since is None) or (event[SenML.TIME_KEY] >= since)
            match_before = (before is None) or (event[SenML.TIME_KEY] < before)
            
            if match_room and match_since and match_before:
                res.append(log)

        return res
    
    def _process_SenML(self, senml):
        # Usa la funzione dal tuo modulo SenMLUtils
        flat_events = SenML.flatten_senml(senml)
        
        for event in flat_events:
            self._insert_new_log(SenML.build_array_dict([event]))

    def _insert_new_log(self, j):
        id = self.id
        self.id += 1
        j["epoch"] = time.time()
        j["id"] = id
        self.logs.append(j)
        return id
    
    def _delete_logs_by_time(self, before):
        res = []
        deleted = []
        for log in self.logs:
            if log[SenML.EVENTS_KEY][0][SenML.TIME_KEY] < before:
                deleted.append(log["id"])
            else:
                res.append(log)
        self.logs = res
        return deleted