import cherrypy
import json
import time

ROOMS = ["living_room", "kitchen", "bedroom"]

def validate_SenML(j):
    try:
        if "bn" not in j.keys() or "e" not in j.keys():
            return False
        for e in j["e"]:
            if "n" not in e.keys() or "u" not in e.keys() or "v" not in e.keys():
                return False
        return True
    except Exception as e:
        return False

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
            data = json.loads(cherrypy.request.body.read())
            if not validate_SenML(data):
                raise cherrypy.HTTPError(400, "Wrong SenML format")
            id = self.id
            self.id += 1
            epoch = time.time()
            self.logs.append({
                "id": id,
                "epoch": epoch,
                "bn": data["bn"],
                "e": data["e"]
            })
            return json.dumps({
                "message": f"Log added with id = {id} and epoch = {epoch}"
            }).encode("utf-8")
        except cherrypy.HTTPError:
            raise
        except Exception as e:
            raise cherrypy.HTTPError(500, str(e))

    def PUT(self, *path, **query):
        raise cherrypy.HTTPError(501, "PUT method not implemented")

    def DELETE(self, *path, **query):
        raise cherrypy.HTTPError(501, "DELETE method not implemented")