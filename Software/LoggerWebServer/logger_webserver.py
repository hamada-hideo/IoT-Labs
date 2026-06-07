import cherrypy
import json
import time
import threading
import os
import paho.mqtt.client as mqtt
import SenMLUtils as SenML

from Catalog.catalog_client import CatalogClient

DIR = os.path.dirname(os.path.abspath(__file__))

class MQTTLoggerBridge:
    def __init__(self, logger_instance):
        self.logger_service = logger_instance
        
        self.broker = "broker.emqx.io"
        self.port = 1883
        
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            client_id=f"EventLog_Group12_{int(time.time())}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print(f"[MQTT Logger] Connesso con successo al Broker su {self.broker}:{self.port}!")
            self.client.subscribe("/tiot/group12/#")
        else:
            print(f"[MQTT Logger] Errore di connessione. Codice: {reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            
            # Il Logger intercetta i dati MQTT e li passa al parser SenML
            if SenML.validate_SenML(payload):
                self.logger_service._process_SenML(payload)
                print(f"[MQTT Logger] Evento salvato con successo da {msg.topic}")
            else:
                # Scarta silenziosamente il traffico non SenML (utile se il topic è affollato)
                # print(f"[MQTT Logger - WARN] Messaggio non SenML scartato da {msg.topic}")
                pass
                
        except json.JSONDecodeError:
            print(f"[MQTT Logger - ERROR] Il payload da {msg.topic} non è un JSON valido.")
        except Exception as e:
            print(f"[MQTT Logger - ERROR] Eccezione durante l'elaborazione del messaggio: {e}")

    def run(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"[MQTT Logger - ERROR] Impossibile avviare il client MQTT: {e}")

class LoggerWebServer():
    exposed = True

    def __init__(self, ip, port, endpoint):
        self.log_file = os.path.join(DIR, "logs.json")
        if os.path.exists(self.log_file):
            with open(self.log_file, "r") as f:
                self.logs = json.load(f)
        else:
            self.logs = []
            with open(self.log_file, "w") as f:
                json.dump(self.logs, f, indent=4)
        self.id_counter = 0
        self.lock = threading.Lock()

        self.ip = ip
        self.port = port
        self.endpoint = endpoint
        self.id = "LoggerWebServer"
        self.data = {
            "id": self.id,
            "description": "Service that logs commands sent to actuators and data received from sensors in the smart home",
            "rest": {
                "url": f"http://{self.ip}:{self.port}/{self.endpoint}",
                "method": ["GET", "POST", "DELETE"]
            }
        }

        self.cc = CatalogClient()

        self.registered = False

        threading.Thread(target=self._try_register_refresh_loop, args = (self.data, self.id), daemon=True).start()
        
        # Facciamo partire il ponte MQTT che ascolta la rete
        self.mqtt_bridge = MQTTLoggerBridge(self)
        self.mqtt_bridge.run()

    def _try_register_refresh_loop(self, payload, id):
        while True:
            time.sleep(self.cc.loop_time)
            if not self.registered:
                if self.cc.register_service(payload):
                    self.registered = True
            else:
                if not self.cc.refresh_service(id):
                    self.registered = False

    def _get_room_name(self, senml_name):
        segments = senml_name.strip().split("/")
        if len(segments) < 2:
            raise cherrypy.HTTPError(400, "Wrong SenML name")
        return segments[1]
    
    def _get_type(self, senml_name):
        segments = senml_name.strip().split("/")
        if len(segments) < 3:
            raise cherrypy.HTTPError(400, "Wrong SenML name")
        return segments[2]

    def _get_logs_by_room_and_time(self, room = None, since = None, before = None):
        res = []
        with self.lock:
            for log in self.logs:
                event = log[SenML.EVENTS_KEY][0]
                room_name = self._get_room_name(event[SenML.NAME_KEY])
                match_room = (room is None) or (room_name == room)
                match_since = (since is None) or (event[SenML.TIME_KEY] >= since)
                match_before = (before is None) or (event[SenML.TIME_KEY] < before)
                
                if match_room and match_since and match_before:
                    res.append(log)
        return res
    
    def _process_SenML(self, senml):
        flat_events = SenML.flatten_senml(senml)
        ids = []
        with self.lock:
            for event in flat_events:
                ids.append(self._insert_new_log(SenML.build_array_dict([event])))
                with open(self.log_file, "w") as f:
                    json.dump(self.logs, f, indent=4)
        return ids

    def _insert_new_log(self, j):
        id = self.id_counter
        self.id_counter += 1
        j["epoch"] = time.time()
        j["id"] = id
        self.logs.append(j)
        return id
    
    def _delete_logs_by_time(self, before):
        res = []
        deleted = []
        with self.lock:
            for log in self.logs:
                if log[SenML.EVENTS_KEY][0][SenML.TIME_KEY] < before:
                    deleted.append(log["id"])
                else:
                    res.append(log)
            self.logs = res
            with open(self.log_file, "w") as f:
                json.dump(self.logs, f, indent=4)
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
        if room and not self._get_logs_by_room_and_time(room):
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
            ids.extend(self._process_SenML(data))
        elif isinstance(data, list):
            for j in data:
                if not SenML.validate_SenML(j):
                    raise cherrypy.HTTPError(422, f"Wrong SenML format: {j}")
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
