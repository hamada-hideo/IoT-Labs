import cherrypy
import json

class MockCatalog:
    exposed = True

    def GET(self, *uri, **params):
        if len(uri) == 0:
            return json.dumps({
                "message": "mock catalog"
            }).encode("utf-8")
        else:
            if uri[0] == "services":
                if len(uri) == 1:
                    return json.dumps({
                        "message": "mock services catalog"
                    }).encode("utf-8")
                elif len(uri) == 2:
                    return json.dumps({
                        "message": f"mock service catalog for {uri[-1]}"
                    }).encode("utf-8")
            elif uri[0] == "devices":
                if len(uri) == 1:
                    return json.dumps({
                        "message": "mock devices catalog"
                    }).encode("utf-8")
                elif len(uri) == 2:
                    return json.dumps({
                        "message": f"mock device catalog for {uri[-1]}"
                    }).encode("utf-8")
            elif uri[0] == "broker":
                return json.dumps({
                    "message": "mock broker data"
                }).encode("utf-8")

    def POST(self, *uri, **path):
        data = cherrypy.request.body.read()
        print(data)
        if uri[0] == "services":
            return json.dumps({
                "message": f"mock service added/refreshed"
            }).encode("utf-8")
        elif uri[0] == "devices":
            return json.dumps({
                "message": f"mock device added/refreshed"
            }).encode("utf-8")
        

if __name__ == "__main__":
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }

    cherrypy.tree.mount(MockCatalog(), "/catalog", conf)

    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': 8080})

    cherrypy.engine.start()
    cherrypy.engine.block()
