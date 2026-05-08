#include <WiFiNINA.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> 
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

const char* broker = "test.mosquitto.org"; 
int port = 1883;

const char* topic_pub = "/tiot/group12/temperature";
const char* topic_sub = "/tiot/group12/led";

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

const int ledPin = 2;
const int tempPin = A0;
unsigned long lastMsgTime = 0;

// Callback asincrona eseguita quando arriva un messaggio su topic_sub
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
    JsonObject event = events[0];
    const char* n = event["n"];
    
    // Controlliamo che il formato sia corretto e mirato al LED 
    if (strcmp(n, "led")==0){
      int v = event["v"]; // valore del LED (1 o 0)
      digitalWrite(ledPin, v ? HIGH : LOW);
      Serial.print("Stato LED aggiornato a: ");
      Serial.println(v);
    } else {
      Serial.println("Nome sensore 'n' non riconosciuto.");
    }
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.println("Connessione al Wi-Fi...");
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
    // ID Univoco del client (genera un nome casuale per evitare conflitti)
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
  mqttClient.loop();

  unsigned long now = millis();
  // Pubblicazione ogni 10 secondi come da specifiche
  if (now - lastMsgTime > 10000) {
    lastMsgTime = now;
    
    float tempVal = analogRead(tempPin) * 0.48828125;
    // Costruiamo la stringa json a mano per il publish (o possiamo usare anche qui ArduinoJson)
    String payload = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"temperature\", \"v\": " + String(tempVal) + ", \"u\": \"Cel\"}]}";
    
    mqttClient.publish(topic_pub, payload.c_str());
    Serial.println("Messaggio pubblicato: " + payload);
  }
}