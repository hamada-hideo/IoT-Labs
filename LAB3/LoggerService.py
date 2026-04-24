import cherrypy
import json

ROOMS = ["living_room", "kitchen", "bedroom"]

class LoggerService():
    exposed = True

    def __init__(self):
        self.logs = [
            {
                "id": 0,
                "epoch": 1777046654.1902337,
                "bn": "living_room/",
                "e": [
                    {
                        "n": "temperature",
                        "u": "°C",
                        "t": 1777046654.1902337,
                        "v": 25
                    },
                    {
                        "n": "humidity",
                        "u": "%RH",
                        "t": 1777046650.1902337,
                        "v": 50
                    }
                ]
            },
            {
                "id": 1,
                "epoch": 1777046660.1902337,
                "bn": "kitchen/",
                "e": [
                    {
                        "n": "temperature",
                        "u": "°C",
                        "t": 1777046654.1902337,
                        "v": 30
                    },
                    {
                        "n": "humidity",
                        "u": "%RH",
                        "t": 1777046650.1902337,
                        "v": 60
                    }
                ]
            }
        ]

    def GET(self, *path, **query):
        try:
            print("yeyyyy")
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
        raise cherrypy.HTTPError(501, "POST method not implemented")

    def PUT(self, *path, **query):
        raise cherrypy.HTTPError(501, "PUT method not implemented")

    def DELETE(self, *path, **query):
        raise cherrypy.HTTPError(501, "DELETE method not implemented")