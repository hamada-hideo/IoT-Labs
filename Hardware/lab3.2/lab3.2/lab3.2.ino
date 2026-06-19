#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include <Arduino_LSM6DSOX.h> // Library for the internal temperature sensor (IMU)
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

// Replace with the local IP address of your PC where main_logger.py is running
char serverAddress[] = "10.108.52.52"; 
int port = 8080; // The LoggerWebServer port defined in your Globals.py

WiFiClient wifi;
HttpClient client = HttpClient(wifi, serverAddress, port);

unsigned long lastExecution = 0;

void setup() {
  Serial.begin(9600);
  
  // Initialization of the internal IMU sensor
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while(1);
  }
  
  Serial.println("Connecting to Wi-Fi...");
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(5000);
    Serial.println("Connection attempt...");
  }
  
  Serial.println("Connected to Wi-Fi!");
}

void loop() {
  unsigned long now = millis();
  
  // Executes the task every 10 seconds as requested by the specifications
  if (now - lastExecution > 10000) {
    lastExecution = now;
    int tempVal = 0;
    
    // Reading the temperature from the internal sensor
    if (IMU.temperatureAvailable()) {
      IMU.readTemperature(tempVal);
    }
    
    // Building the SenML JSON using the read temperature
    String body = "{\"bn\": \"smart_home/kitchen/\", \"e\": [{\"t\": " + String(millis()) + ", \"n\": \"temperature\", \"v\": " + String(tempVal) + ", \"u\": \"Cel\"}]}";
    
    Serial.println("Sending POST to /log with payload: " + body);
    
    // Creation of the POST request using HttpClient as per the slides
    client.beginRequest();
    client.post("/log");
    client.sendHeader("Content-Type", "application/json");
    client.sendHeader("Content-Length", body.length());
    client.beginBody();
    client.print(body);
    client.endRequest();
    
    // Reading and printing the response from the Python server
    int statusCode = client.responseStatusCode();
    String response = client.responseBody();
    
    Serial.print("Status code from the server: ");
    Serial.println(statusCode);
    
    Serial.print("Response from the server: ");
    Serial.println(response);
  }
}
