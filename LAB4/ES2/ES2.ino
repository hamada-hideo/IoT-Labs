#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include <Arduino_LSM6DSOX.h> // Libreria per il sensore di temperatura interno (IMU)
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

// Sostituisci con l'indirizzo IP locale del tuo PC dove è in esecuzione main_logger.py
char serverAddress[] = ""; 
int port =; // La porta del LoggerWebServer definita nel tuo Globals.py

WiFiClient wifi;
HttpClient client = HttpClient(wifi, serverAddress, port);

unsigned long lastExecution = 0;

void setup() {
  Serial.begin(9600);
  
  // Inizializzazione del sensore IMU interno
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while(1);
  }

  Serial.println("Connessione al Wi-Fi in corso...");
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.println("Tentativo di connessione...");
  }
  Serial.println("Connesso al Wi-Fi!");
}

void loop() {
  unsigned long now = millis();
  
  // Esegue il task ogni 10 secondi come richiesto dalle specifiche
  if (now - lastExecution > 10000) {
    lastExecution = now;
    
    int tempVal = 0;
    // Lettura della temperatura dal sensore interno
    if (IMU.temperatureAvailable()) {
      IMU.readTemperature(tempVal);
    }
    
    // Costruzione del JSON SenML usando la temperatura letta
    String body = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"temperature\", \"v\": " + String(tempVal) + ", \"u\": \"Cel\"}]}";

    Serial.println("Invio POST a /log con payload: " + body);

    // Creazione della richiesta POST utilizzando HttpClient come da slide [1]
    client.beginRequest();
    client.post("/log");
    client.sendHeader("Content-Type", "application/json");
    client.sendHeader("Content-Length", body.length());
    client.beginBody();
    client.print(body);
    client.endRequest();

    // Lettura e stampa della risposta dal server Python [1]
    int statusCode = client.responseStatusCode();
    String response = client.responseBody();

    Serial.print("Status code dal server: ");
    Serial.println(statusCode);
    Serial.print("Risposta dal server: ");
    Serial.println(response);
  }
}