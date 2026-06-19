#include <WiFiNINA.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> 
#include <Arduino_LSM6DSOX.h> // Library for the internal temperature sensor (IMU)
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;
const char* broker = "broker.emqx.io";
int port = 1883;

const char* topic_pub = "/tiot/group12/temperature";
const char* topic_sub = "/tiot/group12/led";
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

const int heaterPin = 3; // The LED/Heater moved to pin D3
unsigned long lastMsgTime = 0;

const int capacity = JSON_OBJECT_SIZE(2) + JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(4) + 100;
DynamicJsonDocument doc_snd(capacity);
DynamicJsonDocument doc_rec(capacity);

// Asynchronous callback executed when an incoming SenML command arrives
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message (");
  Serial.print((char*) payload);
  Serial.print(") received on topic: ");
  Serial.println(topic);
  
  DeserializationError error = deserializeJson(doc_snd, (char*) payload, length);
  if (error) {
    Serial.print("Incorrect SenML format! Decoding error: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Extraction of the "e" array
  JsonArray events = doc_snd["e"];
  if (!events.isNull() && events.size() == 1) {
    JsonObject event = events[0];
    const char* n = event["n"];
    
    // We check that the format is correct and targeted to the LED or Heater
    if (n && (String(n) == "led" || String(n) == "heater")) {
      int v = event["v"]; // command value (1 turns ON, 0 turns OFF)
      Serial.println(v);
      if (v == 0 || v == 1) {
        digitalWrite(heaterPin, v ? HIGH : LOW);
        Serial.print("Heater status (pin D3) updated to: ");
        Serial.println(v);
      } else {
        Serial.println("Incorrect value for the LED: " + String(v));
      }
    } else {
      Serial.println("Actuator name 'n' not recognized.");
    }
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(heaterPin, OUTPUT);
  digitalWrite(heaterPin, LOW);
  
  // Initialization of the internal IMU sensor
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while(1);
  }
  
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.println("Connecting to Wi-Fi...");
  }
  Serial.println("Connected to Wi-Fi!");
  
  // Configuration of the MQTT broker and callback
  mqttClient.setServer(broker, port);
  mqttClient.setCallback(callback);
}

void reconnect() {
  // Loop until we are connected
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Generates a unique ID to avoid conflicts with other students on the public broker
    String clientId = "ArduinoClient-" + String(random(0xffff), HEX);
    
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("Connected!");
      // Subscription to the topic upon connection
      mqttClient.subscribe(topic_sub);
    } else {
      Serial.print("Failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

void loop() {
  if (!mqttClient.connected()) {
    reconnect();
  }
  mqttClient.loop(); // Keeps the connection alive and processes incoming messages
  
  unsigned long now = millis();
  
  // Publication every 10 seconds as per specifications
  if (now - lastMsgTime > 10000) {
    lastMsgTime = now;
    int tempVal = 0;
    
    // Safe reading of the temperature from the IMU sensor
    if (IMU.temperatureAvailable()) {
      IMU.readTemperature(tempVal);
    }
    
    // SenML JSON string construction
    String payload = senMLEncodeTemperature(tempVal);
    mqttClient.publish(topic_pub, payload.c_str());
    
    Serial.print("Published on ");
    Serial.print(topic_pub);
    Serial.print(" : ");
    Serial.println(payload);
  }
}

String senMLEncodeTemperature(int val) {
  doc_snd.clear();
  doc_snd["bn"] = "ArduinoGroup12";
  doc_snd["e"][0]["t"] = millis();
  doc_snd["e"][0]["n"] = "temperature";
  doc_snd["e"][0]["v"] = val;
  doc_snd["e"][0]["u"] = "Cel";
  
  String output;
  serializeJson(doc_snd, output);
  return output;
}
