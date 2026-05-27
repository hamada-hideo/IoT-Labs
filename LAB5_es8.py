#EXERCISE VIII
import paho.mqtt.client as mqtt
import json
import time
import threading


HOST = "iot.eclipse.org"
PORT = 1883

class DeviceMQTTClient():
    def __init__(self):

        self.client_id = "device_001"
        self.client = mqtt.Client(client_id = self.client_id)
        self.running = True


        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.register_topic = "/tiot/group12/catalog/register"
        self.ack_topic = f"/tiot/group12/catalog/ack/{self.client_id}"
        self.query_response_topic = "/tiot/group12/catalog/query/response"

        self.client.connect(HOST, PORT)

        self.reg_thread = threading.Thread(target = self._registration_loop, daemon=True)
        self.reg_thread.start()
    def on_connect(self,client,userdata,flags,rc):
        if(rc == 0):
            print("Connection success")
        else:
            print(f"Connection failed, with error code : {rc}")
            return
        self.client.subscribe(self.ack_topic)
        self.client.subscribe(self.query_response_topic)

    def on_message(self,client,userdata,msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            print(f"Received a malformed message in {topic}")
            return
        if(topic == self.ack_topic):
            print(f"ACK RECEIVED: {data}")
        elif(topic == self.query_response_topic):
            print(f"Query response: {data}")
        else:
            print(f"Unknown topic: {data}")

    def _build_payload(self):
        payload_dict = {
        "id" : self.client_id,
        "description": "IoT temperature device",
        "endpoint": None,
        "mqtt":{
            "ip": HOST,
            "port": PORT,
            "topic": self.register_topic
        },
        "resources": ["temperature"],
        "insert_timestamp": time.time()
        }
        return json.dumps(payload_dict)
    def _registration_loop(self):
        while self.running:
            payload = self._build_payload()
            self.client.publish(self.register_topic,payload)
            print("Registration complete")
            time.sleep(60)
    def run(self):
        self.client.loop_start()
        while(self.running):
            print("\n1. Register now")
            print("2. Query all devices")
            print("3. Query device by ID")
            print("4. Quit")
            choice = input("Choose an option: ")
            if(choice == "1"):
                payload = self._build_payload()
                self.client.publish(self.register_topic, payload)
                print("Registration complete")
            elif(choice == "2"):
                self.client.publish(self.query_response_topic, json.dumps({"action":"get_all"}))
            elif(choice == "3"):
                device_id = input("Entire device ID: ")
                self.client.publish(self.query_response_topic, json.dumps({"action": "get_by_id", "id": device_id}))
            elif(choice == "4"):
                self.running = False
                self.client.loop_stop()
                self.client.disconnect()
                print("Disconnected")

if __name__ == "__main__":
    device  = DeviceMQTTClient()
    device.run()
    print("ただいま~")
