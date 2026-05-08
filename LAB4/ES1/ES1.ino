#include <WiFiNINA.h>
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;
WiFiServer server(80);

const int ledPin = 2;   // Sostituisci con il pin a cui hai collegato il LED (o LED_BUILTIN)
const int tempPin = A0; // Sostituisci con il pin del sensore analogico (o sensore interno)

void setup() {
  Serial.begin(9600);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  Serial.println("Connessione al Wi-Fi...");
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.println("Tentativo di connessione in corso...");
  }
  
  server.begin();
  Serial.print("Server HTTP avviato. IP: ");
  Serial.println(WiFi.localIP());
}

void printResponse(WiFiClient client, int code, String body) {
  client.println("HTTP/1.1 " + String(code));
  if (code == 200) {
    client.println("Content-type: application/json; charset=utf-8"); // Migliora la formattazione nel browser
    client.println(); // Riga vuota obbligatoria
    client.println(body);
  } else {
    client.println("Content-type: application/json; charset=utf-8"); // Diciamo che anche l'errore è in formato JSON
    client.println(); // Riga vuota obbligatoria per chiudere gli header
    client.println(body); // Stampiamo finalmente il messaggio di errore JSON!
  }
}

void loop() {
  WiFiClient client = server.available();
  if (client) {
    if (client.connected()) {
      // Estrazione del metodo e dell'URL come mostrato nelle slide
      String req_type = client.readStringUntil(' ');
      req_type.trim();
      String url = client.readStringUntil(' ');
      url.trim();

      // Consuma il resto degli header della richiesta HTTP
      while (client.available()) {
        String line = client.readStringUntil('\n');
        if (line.length() == 1 && line == '\r') { break; }
      }

      Serial.println("Ricevuta richiesta " + req_type + " per " + url);

      // Gestione del routing
      if (req_type == "GET") {
        if (url == "/temperature") {
          // Lettura sensore (esempio fittizio, adatta alla curva del tuo sensore)
          float tempVal = analogRead(tempPin) * 0.48828125; 
          String body = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"temperature\", \"v\": " + String(tempVal) + ", \"u\": \"Cel\"}]}";
          printResponse(client, 200, body);
          
        } else if (url == "/led/1") {
          digitalWrite(ledPin, HIGH);
          String body = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"led\", \"v\": 1, \"u\": null}]}";
          printResponse(client, 200, body);
          
        } else if (url == "/led/0") {
          digitalWrite(ledPin, LOW);
          String body = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"led\", \"v\": 0, \"u\": null}]}";
          printResponse(client, 200, body);
          
        } else {
          printResponse(client, 404, "{\"error\": \"Resource not found\"}");
        }
      } else {
        printResponse(client, 400, "{\"error\": \"Method not supported\"}");
      }
    }
    delay(10);
    client.stop();
  }
}
