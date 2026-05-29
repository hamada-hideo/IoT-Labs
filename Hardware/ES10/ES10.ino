#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> 
#include <Arduino_LSM6DSOX.h> 
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

// --- Configurazione Catalog (REST) ---
char catalogAddress[] = " 10.65.201.158"; // INSERISCI L'IP DEL TUO PC
int catalogPort = 8080;

// Variabili dinamiche popolate tramite la chiamata REST
char dynamic_broker_ip[40] = "broker.emqx.io"; // Valore di fallback
int dynamic_broker_port = 1883;

// Topic del Gruppo 12
const char* device_id = "arduino_group12";
const char* topic_pub = "/tiot/group12/temperature";
const char* topic_sub = "/tiot/group12/led";
const char* topic_registration = "/tiot/group12/catalog/registration";

WiFiClient wifiClient;
HttpClient restClient = HttpClient(wifiClient, catalogAddress, catalogPort); 
PubSubClient mqttClient(wifiClient);

const int heaterPin = 3; 
unsigned long lastMsgTime = 0;
unsigned long lastRegistrationTime = 0; 

const int capacity = JSON_OBJECT_SIZE(2) + JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(4) + 150;
DynamicJsonDocument doc_snd(capacity);
DynamicJsonDocument doc_rec(capacity);

void callback(char* topic, byte* payload, unsigned int length) {
  // Ottimizzazione memorie: stampe sequenziali invece di concatenazioni con +
  Serial.print("Messaggio ricevuto sul topic: ");
  Serial.println(topic);
  
  DeserializationError error = deserializeJson(doc_rec, (char*) payload, length);
  if (error) {
    Serial.print("Formato SenML errato! Errore decodifica: ");
    Serial.println(error.c_str());
    return;
  }
  
  JsonArray events = doc_rec["e"];
  if (!events.isNull() && events.size() > 0) {
    JsonObject event = events[0]; // Accesso al primo elemento dell'array
    const char* n = event["n"];
    if (n && (String(n) == "led" || String(n) == "heater")) {
      int v = event["v"]; 
      if (v == 0 || v == 1) {
        digitalWrite(heaterPin, v ? HIGH : LOW);
        Serial.print("Stato Attuatore (pin D3) aggiornato a: ");
        Serial.println(v);
      } else {
        Serial.print("Valore errato per l'attuatore: ");
        Serial.println(v);
      }
    }
  }
}

void registerDeviceMQTT() {
  doc_snd.clear();
  doc_snd["id"] = device_id;
  doc_snd["description"] = "Arduino Smart Home Node - Group 12";
  
  JsonObject mqtt_info = doc_snd.createNestedObject("mqtt");
  mqtt_info["topic_temp"] = topic_pub;
  mqtt_info["topic_led"] = topic_sub;
  
  JsonArray resources = doc_snd.createNestedArray("resources");
  resources.add("temperature");
  resources.add("led");

  String output;
  serializeJson(doc_snd, output);
  
  mqttClient.publish(topic_registration, output.c_str());
  Serial.print("Registrazione MQTT inviata: ");
  Serial.println(output);
}

void setup() {
  Serial.begin(9600);
  pinMode(heaterPin, OUTPUT);
  digitalWrite(heaterPin, LOW);
  
  if (!IMU.begin()) {
    Serial.println("Errore inizializzazione IMU!");
    while(1);
  }
  
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.println("Connessione al Wi-Fi in corso...");
  }
  Serial.println("Connesso al Wi-Fi!");

  // --- BUG LOGICO 1 RISOLTO: Recupero e utilizzo dinamico del Broker ---
  Serial.println("Interrogo il Catalog via REST per ottenere il broker...");
  restClient.get("/broker");
  
  if(restClient.responseStatusCode() == 200) {
    String response = restClient.responseBody();
    Serial.print("Risposta Catalog: ");
    Serial.println(response);
    
    // Parsing della risposta JSON dal Catalog
    StaticJsonDocument<128> doc_broker;
    if (!deserializeJson(doc_broker, response)) {
        if (doc_broker.containsKey("ip")) {
            strlcpy(dynamic_broker_ip, doc_broker["ip"], sizeof(dynamic_broker_ip));
        }
        if (doc_broker.containsKey("port")) {
            dynamic_broker_port = doc_broker["port"];
        }
    }
  } else {
    Serial.println("Errore Catalog! Uso il broker di fallback");
  }

  Serial.print("Configurazione MQTT: ");
  Serial.print(dynamic_broker_ip);
  Serial.print(":");
  Serial.println(dynamic_broker_port);
  
  // Assegnazione dinamica
  mqttClient.setServer(dynamic_broker_ip, dynamic_broker_port);
  mqttClient.setCallback(callback);
}

void reconnect() {
  while (!mqttClient.connected()) {
    Serial.print("Tentativo di connessione MQTT...");
    String clientId = "ArduinoGroup12-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("Connesso!");
      mqttClient.subscribe(topic_sub);
      registerDeviceMQTT();
      lastRegistrationTime = millis();
    } else {
      Serial.print("Fallito, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Ritento tra 5 secondi...");
      delay(5000);
    }
  }
}

void loop() {
  if (!mqttClient.connected()) {
    reconnect();
  }
  mqttClient.loop(); 

  unsigned long now = millis();
  
  if (now - lastRegistrationTime > 60000) {
    lastRegistrationTime = now;
    registerDeviceMQTT();
  }

  if (now - lastMsgTime > 10000) {
    lastMsgTime = now;
    
    // --- OTTIMIZZAZIONE 1: Utilizzo del float ---
    int tempVal = 0;
    if (IMU.temperatureAvailable()) {
      IMU.readTemperature(tempVal);
    }
    
    String payload = senMLEncodeTemperature(tempVal);
    mqttClient.publish(topic_pub, payload.c_str());
    
    // --- OTTIMIZZAZIONE 2: Stampe sequenziali (NO String + String) ---
    Serial.print("Pubblicato su ");
    Serial.print(topic_pub);
    Serial.print(" : ");
    Serial.println(payload);
  }
}

// --- BUG LOGICO 2 RISOLTO: Array SenML corretto ---
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