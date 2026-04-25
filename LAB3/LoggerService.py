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
        try:
            room = None
            since = None
            if len(path) == 0:
                if "room" in query.keys():
                    room = query["room"]
                if "since" in query.keys():
                    try:
                        since = float(query["since"])
                    except ValueError:
                        raise cherrypy.HTTPError(400, "Timestamp must be a float")
            else:
                room = path[0]
            if room is not None and room not in ROOMS:
                raise cherrypy.HTTPError(404, f"Room {room} not found")
            res = [log for log in self.logs if ((room is None or room == log["bn"][:-1]) and (since is None or since <= log["epoch"]))]
            return json.dumps(res).encode("utf-8")
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            raise cherrypy.HTTPError(500, str(e))

    def POST(self, *path, **query):
        try:
            ids = []
            data = json.loads(cherrypy.request.body.read())
            if isinstance(data, dict):
                if not validate_SenML(data):
                    raise cherrypy.HTTPError(400, f"Wrong SenML format: {data}")
                id = self.__insert_new_log__(data)
                ids.append(id)
            elif isinstance(data, list):
                for j in data:
                    if not validate_SenML(j):
                        raise cherrypy.HTTPError(400, f"Wrong SenML format: {j}")
                    id = self.__insert_new_log__(j)
                    ids.append(id)
            else:
                raise cherrypy.HTTPError(400, "Wrong format, expecting a SenML json or an array of SenML json")
            return json.dumps({
                "message": f"{len(ids)} logs added with ids = {ids}",
            }).encode("utf-8")
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            raise cherrypy.HTTPError(500, str(e))

    def PUT(self, *path, **query):
        raise cherrypy.HTTPError(501, "PUT method not implemented")

    def DELETE(self, *path, **query):
        try:
            try:
                before = float(query["before"])
            except KeyError:
                raise cherrypy.HTTPError(400, "Missing before parameter")
            except ValueError:
                raise cherrypy.HTTPError(400, "Timestamp must be a float")
            res = []
            deleted = []
            for log in self.logs:
                if log["epoch"] < before:
                    deleted.append(log["id"])
                else:
                    res.append(log)
            self.logs = res
            return json.dumps({
                "message": f"{len(deleted)} logs deleted with ids = {deleted}"
            }).encode("utf-8")
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            raise cherrypy.HTTPError(500, str(e))
    
    def __insert_new_log__(self, j):
        id = self.id
        self.id += 1
        epoch = time.time()
        self.logs.append({
            "id": id,
            "epoch": epoch,
            "bn": j["bn"],
            "e": j["e"]
        })
        return id