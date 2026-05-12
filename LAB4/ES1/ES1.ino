#include <WiFiNINA.h>
#include <Arduino_LSM6DSOX.h> // Libreria per usare il sensore di temperatura interno (IMU)
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;
WiFiServer server(80);
const int heaterPin = 3; // Il LED che simula l'heater è ora sul pin D3

void setup() {
  Serial.begin(9600);
  pinMode(heaterPin, OUTPUT);
  digitalWrite(heaterPin, LOW);
  // Inizializzazione del sensore IMU interno
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while(1);
  }
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
  client.println("Content-type: application/json; charset=utf-8"); 
  client.println(); 
  client.println(body);
}
void loop() {
  WiFiClient client = server.available();
  if (client) {
    if (client.connected()) {     
      String req_type = client.readStringUntil(' ');
      req_type.trim();
      String url = client.readStringUntil(' ');
      url.trim();
      while (client.available()) {
        String line = client.readStringUntil('\n');
        if (line.length() == 1 && line == "\r") { break; }
      }
      Serial.println("Ricevuta richiesta " + req_type + " per " + url);
      if (req_type == "GET") {
        if (url == "/temperature") {
          int tempVal = 0;
          // Lettura della temperatura dal sensore IMU interno
          if (IMU.temperatureAvailable()) {
            IMU.readTemperature(tempVal);
          }
          String body = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"temperature\", \"v\": " + String(tempVal) + ", \"u\": \"Cel\"}]}";
          printResponse(client, 200, body);  
        } else if (url.startsWith("/heater/") || url.startsWith("/led/")) {
          String led_val = "";
          if (url.startsWith("/heater/")) { // Accetta entrambi gli URI
            led_val = url.substring(8);
          } else if (url.startsWith("/led/")) { // Accetta entrambi gli URI
            led_val = url.substring(5);
          } 
          if (led_val == "0" || led_val == "1") {
            int int_val = led_val.toInt();
            digitalWrite(heaterPin, int_val);
            String body = "{\"bn\": \"ArduinoGroup12\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"heater\", \"v\": " + led_val + ", \"u\": null}]}";
            printResponse(client, 200, body);
          } else {
            printResponse(client, 400, "{\"error\": \"Invalid output value: " + led_val + "\"}");
          }
        } else {
          printResponse(client, 404, "{\"error\": \"Resource not found: " + url + "\"}");
        }
      } else {
        printResponse(client, 405, "{\"error\": \"Method not supported: " + req_type + "\"}");
      }
    }
    delay(10);
    while (client.available()) {
      client.read();
    }
    client.stop();
  }
}