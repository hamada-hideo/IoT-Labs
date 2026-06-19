import cherrypy
import json
import time

class LoggerWebServer():
    exposed = True

    def __init__(self):
        self.logs = []
        self.id = 0

    def _get_room_name(self, senml_name):
        segments = senml_name.strip().split("/")
        return segments[1]
    
    def _get_type(self, senml_name):
        segments = senml_name.strip().split("/")
        return segments[2]

    def _get_logs_by_room_and_time(self, room = None, since = None, before = None):
        res = []
        for log in self.logs:
            event = log["e"][0]

            # Checks if the room is present in the absolute name (bn+n)
            room_name = self._get_room_name(event["n"])
            match_room = (room is None) or (room_name == room)
            
            # Checks the absolute time of the event (bt+t)
            match_since = (since is None) or (event["t"] >= since)
            match_before = (before is None) or (event["t"] < before)
            
            if match_room and match_since and match_before:
                res.append(log)

        return res
    
    def _process_SenML(self, senml):
        # Uses the function from your SenMLUtils module
        flat_events = self.flatten_senml(senml)
        
        ids = []
        for event in flat_events:
            ids.append(self._insert_new_log(self.build_array_dict([event])))
        return ids

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
            if log["e"][0]["t"] < before:
                deleted.append(log["id"])
            else:
                res.append(log)
        self.logs = res
        return deleted

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
            ids.extend(self._process_SenML(data))
        elif isinstance(data, list):
            for j in data:
                ids.extend(self._process_SenML(j))
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

    def flatten_senml(self, senml_doc):
        """
        Takes a SenML dictionary as input and returns a list of "flat" events,
        in which the base-name (bn) and base-time (bt) have been resolved inside 
        each individual event.
        """
        flattened_events = []
        
        # Extract bn and bt (with default values if not present)
        bn = senml_doc.get("bn", "")
        bt = senml_doc.get("bt", 0.0)
        
        for event in senml_doc.get("e", []):
            n = event.get("n", "")
            t = event.get("t", 0.0)
            
            # Create a flat event by resolving IETF SenML rules
            flat_event = {
                "n": bn + n,      # Absolute name of the resource
                "t": bt + t,      # Absolute timestamp of the event
                "v": event.get("v"),
                "u": event.get("u")
            }
            flattened_events.append(flat_event)
            
        return flattened_events
    
    def build_array_dict(self, event_array, basename = None, basetime = None):
        res = {"e": event_array}
        if basename is not None:
            res["bn"] = basename
        if basetime is not None:
            res["bt"] = basetime
        return res
    
if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }

    cherrypy.tree.mount(LoggerWebServer(), f"/log", conf)

    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': 8080})

    cherrypy.engine.start()
    cherrypy.engine.block()