#include <WiFiNINA.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> 
#include <Arduino_LSM6DSOX.h> // Libreria per il sensore di temperatura interno (IMU)
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;
const char* broker = "broker.emqx.io";
int port = 1883;

const char* topic_pub = "/tiot/group12/temperature";
const char* topic_sub = "/tiot/group12/led";
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

const int heaterPin = 3; // Il LED/Heater spostato sul pin D3
unsigned long lastMsgTime = 0;

const int capacity = JSON_OBJECT_SIZE(2) + JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(4) + 100;
DynamicJsonDocument doc_snd(capacity);
DynamicJsonDocument doc_rec(capacity);

// Callback asincrona eseguita quando arriva un comando SenML in entrata
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Messaggio (");
  Serial.print((char*) payload);
  Serial.print(") ricevuto sul topic: ");
  Serial.println(topic);
  DeserializationError error = deserializeJson(doc_snd, (char*) payload, length);
  if (error) {
    Serial.print("Formato SenML errato! Errore decodifica: ");
    Serial.println(error.c_str());
    return;
  }
  // Estrazione dell'array "e"
  JsonArray events = doc_snd["e"];
  if (!events.isNull() && events.size() == 1) {
    JsonObject event = events[0];
    const char* n = event["n"];
    // Controlliamo che il formato sia corretto e mirato al LED o Heater
    if (n && (String(n) == "led" || String(n) == "heater")) {
      int v = event["v"]; // valore del comando (1 accende, 0 spegne)
      Serial.println(v);
      if (v == 0 || v == 1) {
        digitalWrite(heaterPin, v ? HIGH : LOW);
        Serial.print("Stato Heater (pin D3) aggiornato a: ");
        Serial.println(v);
      } else {
        Serial.println("Valore errato per il led: " + String(v));
      }
    } else {
      Serial.println("Nome attuatore 'n' non riconosciuto.");
    }
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(heaterPin, OUTPUT);
  digitalWrite(heaterPin, LOW);
  // Inizializzazione del sensore IMU interno
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while(1);
  }
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.println("Connessione al Wi-Fi in corso...");
  }
  Serial.println("Connesso al Wi-Fi!");
  // Configurazione del broker MQTT e della callback
  mqttClient.setServer(broker, port);
  mqttClient.setCallback(callback);
}

void reconnect() {
  // Loop finché non siamo connessi
  while (!mqttClient.connected()) {
    Serial.print("Tentativo di connessione MQTT...");
    // Genera un ID univoco per evitare conflitti con altri studenti sul broker pubblico
    String clientId = "ArduinoClient-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("Connesso!");
      // Iscrizione al topic al momento della connessione
      mqttClient.subscribe(topic_sub);
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
  mqttClient.loop(); // Mantiene viva la connessione e processa i messaggi in entrata
  unsigned long now = millis();
  // Pubblicazione ogni 10 secondi come da specifiche
  if (now - lastMsgTime > 10000) {
    lastMsgTime = now;
    int tempVal = 0;
    // Lettura sicura della temperatura dal sensore IMU
    if (IMU.temperatureAvailable()) {
      IMU.readTemperature(tempVal);
    }
    // Costruzione stringa JSON SenML
    String payload = senMLEncodeTemperature(tempVal);
    mqttClient.publish(topic_pub, payload.c_str());
    Serial.println("Messaggio pubblicato: " + payload + "per il topic: " + topic_pub);
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