class ActuatorControlWebServer:
    exposed = True

    def GET(self, *path, **query):
        return b"Hello from the mock actuator control webserver"