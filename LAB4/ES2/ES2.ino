#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

// Sostituisci con l'indirizzo IP locale del tuo PC dove è in esecuzione il LoggerWebServer 
char serverAddress[] = ""; 
int port = 8081; // La porta che abbiamo assegnato nel tuo Globals.py

WiFiClient wifi;
HttpClient client = HttpClient(wifi, serverAddress, port);
const int tempPin = A0;
unsigned long lastExecution = 0;

void setup() {
  Serial.begin(9600);
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.println("Connessione al Wi-Fi in corso...");
  }
  Serial.println("Connesso al Wi-Fi!");
}

void loop() {
  unsigned long now = millis();
  
  // Esegue il task ogni 10 secondi
  if (now - lastExecution > 10000) {
    lastExecution = now;
    
    float tempVal = analogRead(tempPin) * 0.48828125; 
    String body = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"temperature\", \"v\": " + String(tempVal) + ", \"u\": \"Cel\"}]}";

    Serial.println("Invio POST a /log con payload: " + body);

    // Creazione della richiesta POST utilizzando HttpClient come da slide
    client.beginRequest();
    client.post("/log");
    client.sendHeader("Content-Type", "application/json");
    client.sendHeader("Content-Length", body.length());
    client.beginBody();
    client.print(body);
    client.endRequest();

    // Stampa del codice di stato restituito dal server
    int statusCode = client.responseStatusCode();
    String response = client.responseBody();

    Serial.print("Status code dal server: ");
    Serial.println(statusCode);
    Serial.print("Risposta dal server: ");
    Serial.println(response);
  }
}
