#include <WiFiNINA.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> 
#include <Arduino_LSM6DSOX.h> // Libreria per il sensore di temperatura interno (IMU)
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;
const char* broker = "test.mosquitto.org";
int port = 1883;

// Ricordati di cambiare "groupXX" con il tuo gruppo reale
const char* topic_pub = "/tiot/group12/temperature";
const char* topic_sub = "/tiot/group12/led";
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

const int heaterPin = 3; // Il LED/Heater spostato sul pin D3
unsigned long lastMsgTime = 0;
// Callback asincrona eseguita quando arriva un comando SenML in entrata
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Messaggio ricevuto sul topic: ");
  Serial.println(topic);
  // Buffer per ArduinoJson per la decodifica sicura
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  if (error) {
    Serial.print("Formato SenML errato! Errore decodifica: ");
    Serial.println(error.c_str());
    return;
  }
  // Estrazione dell'array "e"
  JsonArray events = doc["e"];
  if (!events.isNull() && events.size() > 0) {
    JsonObject event = events;
    const char* n = event["n"];
    // Controlliamo che il formato sia corretto e mirato al LED o Heater
    if (n && (String(n) == "led" || String(n) == "heater")) {
      int v = event["v"]; // valore del comando (1 accende, 0 spegne)
      digitalWrite(heaterPin, v ? HIGH : LOW);
      Serial.print("Stato Heater (pin D3) aggiornato a: ");
      Serial.println(v);
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
    String payload = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"temperature\", \"v\": " + String(tempVal) + ", \"u\": \"Cel\"}]}";
    mqttClient.publish(topic_pub, payload.c_str());
    Serial.println("Messaggio pubblicato: " + payload);
  }
}