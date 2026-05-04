import cherrypy
import json
import time
from utils import *

class LoggerService():
    exposed = True

    def __init__(self):
        self.logs = []
        self.id = 0

    def GET(self, *path, **query):
        room = None
        since = None
        before = None
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
                raise cherrypy.HTTPError(400, "Timestamp must be a float")
        if "before" in query.keys():
            try:
                before = float(query["before"])
            except ValueError:
                raise cherrypy.HTTPError(400, "Timestamp must be a float")
        if room is not None and room not in ROOMS:
            raise cherrypy.HTTPError(404, f"Room {room} not found")
        return json.dumps(self.__get_logs_by_room_and_time__(room, since, before)).encode("utf-8")

    def POST(self, *path, **query):
        ids = []
        data = json.loads(cherrypy.request.body.read())
        if isinstance(data, dict):
            if not validate_SenML(data):
                raise cherrypy.HTTPError(422, f"Wrong SenML format: {data}")
            id = self.__insert_new_log__(data)
            ids.append(id)
        elif isinstance(data, list):
            for j in data:
                if not validate_SenML(j):
                    raise cherrypy.HTTPError(422, f"Wrong SenML format: {j}")
                id = self.__insert_new_log__(j)
                ids.append(id)
        else:
            raise cherrypy.HTTPError(400, "Wrong format, expecting a SenML json or an array of SenML json")
        return json.dumps({
            "message": f"{len(ids)} logs added with ids = {ids}",
        }).encode("utf-8")

    def DELETE(self, *path, **query):
        try:
            before = float(query["before"])
        except KeyError:
            raise cherrypy.HTTPError(400, "Missing before parameter")
        except ValueError:
            raise cherrypy.HTTPError(400, "Timestamp must be a float")
        deleted = self.__delete_logs_by_time__(before)
        return json.dumps({
            "message": f"{len(deleted)} logs deleted with ids = {deleted}"
        }).encode("utf-8")

    def __get_logs_by_room_and_time__(self, room = None, since = None, before = None):
        return [log for log in self.logs if ((room is None or room == log["bn"][:-1]) and (since is None or since <= log["bt"]) and (before is None or before > log["bt"]))]

    def __insert_new_log__(self, j):
        id = self.id
        self.id += 1
        epoch = time.time()
        self.logs.append({
            "id": id,
            "epoch": epoch,
            "bn": j["bn"],
            "bt": j["bt"],
            "e": j["e"]
        })
        return id
    
    def __delete_logs_by_time__(self, before):
        res = []
        deleted = []
        for log in self.logs:
            if log["bt"] < before:
                deleted.append(log["id"])
            else:
                res.append(log)
        self.logs = res
        return deleted