#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Arduino_LSM6DSOX.h> 
#include <PDM.h>              
#include "arduino_secrets.h" 
#include <LiquidCrystal_PCF8574.h> 

char ssid[] = SECRET_SSID; 
char pass[] = SECRET_PASS; 

// --- IP ESTRATTO DAI SECRETS PER FACILITARE IL DEPLOYMENT ---
const char* catalog_address = SECRET_CATALOG_IP; 
int catalog_port = 8080; 

String broker_address = "";
int broker_port = 1883;

const String NODE_ID = SECRET_NODE_ID; 
const String BASE_TOPIC = "/tiot/group12/smart_home/" + NODE_ID + "/"; 
const String REGISTRATION_URL = "/catalog/devices";

WiFiClient wifi; 
PubSubClient mqtt_client(wifi); 
HttpClient http_client = HttpClient(wifi, catalog_address, catalog_port);

StaticJsonDocument<512> doc_catalog_rx; 
StaticJsonDocument<384> doc_snd; 
StaticJsonDocument<512> doc_rec;  
StaticJsonDocument<512> doc_reg; 

LiquidCrystal_PCF8574 lcd(0x27);

const int GLED_PIN = 2; 
const int LED_PIN = 3;  
const int PIR_PIN = 4;
const int FAN_PIN = 5; 

unsigned long last_publish = 0;
short sampleBuffer[256];
volatile int samplesRead = 0;
float current_noise_peak = 0.0;

float clapThresh = 30000.0; 
int nClaps = 2;
int clapInterval = 3000; 
int clapDuration = 200; 

bool isRunning = true; 

// Variabili di stato reale
bool current_red_light = false; 
bool current_green_light = false;
int current_fan_percent = 0;

void reconnect();
void onPDMdata();

void setup() {
  Serial.begin(9600);
  
  pinMode(FAN_PIN, OUTPUT); 
  pinMode(LED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  
  lcd.begin(16, 2);
  lcd.setBacklight(255);
  lcd.clear();
  lcd.print("Connessione...");

  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connessione WiFi...");
  }
  Serial.println("WiFi Connesso!");

  if (!IMU.begin()) Serial.println("Errore IMU!");
  PDM.onReceive(onPDMdata);
  PDM.begin(1, 16000);

  Serial.println("Recupero info broker dal Catalogo REST...");
  http_client.get("/catalog/broker"); 
  int get_statusCode = http_client.responseStatusCode();
  String get_response = http_client.responseBody();
  http_client.stop();

  if (get_statusCode == 200) {
    DeserializationError err = deserializeJson(doc_catalog_rx, get_response);
    if (!err && doc_catalog_rx["ip"] != "null") {
      broker_address = doc_catalog_rx["ip"].as<String>();
      broker_port = doc_catalog_rx["port"].as<int>();
    } else {
      broker_address = "broker.emqx.io";
    }
  } else {
    broker_address = "broker.emqx.io";
  }

  const char* actuators[][3] = {
    {"heater", "heater", "bool"},
    {"green_lights", "green_lights", "bool"},
    {"fan", "fan", "percent"},
    {"lcd", "lcd", "string"}
  };

  for(int i = 0; i < 4; i++) {
    doc_reg.clear();
    String dev_id = NODE_ID + "/" + String(actuators[i][0]);
    doc_reg["id"] = dev_id;
    doc_reg["description"] = "Modular Edge Node Component";
    
    JsonObject res = doc_reg.createNestedObject("resources");
    res["type"] = actuators[i][1];
    res["unit"] = actuators[i][2];

    JsonObject mqtt_info = doc_reg.createNestedObject("mqtt");
    mqtt_info["command_topic"] = BASE_TOPIC + String(actuators[i][0]) + "/config";
    mqtt_info["feedback_topic"] = BASE_TOPIC + String(actuators[i][0]) + "/state";

    String reg_body;
    serializeJson(doc_reg, reg_body);
    http_client.post(REGISTRATION_URL, "application/json", reg_body);
    http_client.responseStatusCode();
    http_client.responseBody(); 
    http_client.stop();
    Serial.println("Catalog Device aggiunto ed indicizzato: " + dev_id);
  }
  lcd.clear(); lcd.print("Reg. REST OK!"); delay(1000);

  mqtt_client.setServer(broker_address.c_str(), broker_port);
  mqtt_client.setCallback(callback);
}

void loop() {
  if (!mqtt_client.connected()) reconnect(); 
  mqtt_client.loop(); 

  if (samplesRead) {
    static int k = 0; 
    static unsigned long begTime = 0;
    static unsigned long lastClapTime = millis(); 

    for (int i = 0; i < samplesRead; i++) {
      int a = abs(sampleBuffer[i]); 
      if (a > current_noise_peak) current_noise_peak = a;
      if (!isRunning) continue;

      if(a > clapThresh && (millis() - lastClapTime) > clapDuration) {
        if(k == 0) begTime = millis();
        k++;
        lastClapTime = millis();

        if(k % nClaps == 0 && (lastClapTime - begTime) < clapInterval) {
          StaticJsonDocument<256> doc_event;
          doc_event["bn"] = BASE_TOPIC;
          JsonArray ev_arr = doc_event.createNestedArray("e");
          JsonObject ev_obj = ev_arr.createNestedObject();
          ev_obj["n"] = "noise_event";
          ev_obj["v"] = true; ev_obj["u"] = "bool"; ev_obj["t"] = millis() / 1000.0;

          String event_output;
          serializeJson(doc_event, event_output);
          mqtt_client.publish("/tiot/group12/sensors/telemetry", event_output.c_str());
          
          Serial.println("[CLAP EVENT] Inviato a Python.");
          k = 0; 
        }
      }
    }
    samplesRead = 0;
  }

  if (!isRunning) return; 

  if (millis() - last_publish > 10000) { 
    int raw_temp = 25; 
    if (IMU.temperatureAvailable()) IMU.readTemperature(raw_temp);
    
    doc_snd.clear(); 
    doc_snd["bn"] = BASE_TOPIC; 
    JsonArray events = doc_snd.createNestedArray("e");

    JsonObject ev_temp = events.createNestedObject();
    ev_temp["n"] = "temperature"; ev_temp["v"] = (float)raw_temp; ev_temp["u"] = "Cel"; ev_temp["t"] = millis() / 1000.0;

    JsonObject ev_motion = events.createNestedObject();
    ev_motion["n"] = "motion"; ev_motion["v"] = (bool)digitalRead(PIR_PIN); ev_motion["u"] = "bool"; ev_motion["t"] = millis() / 1000.0;

    JsonObject ev_heater = events.createNestedObject();
    ev_heater["n"] = "heater"; ev_heater["v"] = current_red_light; ev_heater["u"] = "bool"; ev_heater["t"] = millis() / 1000.0;

    JsonObject ev_glights = events.createNestedObject();
    ev_glights["n"] = "green_lights"; ev_glights["v"] = current_green_light; ev_glights["u"] = "bool"; ev_glights["t"] = millis() / 1000.0;

    JsonObject ev_fan = events.createNestedObject();
    ev_fan["n"] = "fan"; ev_fan["v"] = current_fan_percent; ev_fan["u"] = "percent"; ev_fan["t"] = millis() / 1000.0;

    String output; 
    serializeJson(doc_snd, output); 
    mqtt_client.publish("/tiot/group12/sensors/telemetry", output.c_str()); 
    last_publish = millis();
  }
}

void onPDMdata() {
  int bytesAvailable = PDM.available();
  PDM.read(sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;
}

void callback(char* topic, byte* payload, unsigned int length) { 
  DeserializationError err = deserializeJson(doc_rec, (char*) payload); 
  if (err) return; 

  String topicStr = String(topic);
  topicStr.replace(BASE_TOPIC, ""); 
  topicStr.replace("/config", ""); 
  String target_actuator = topicStr;

  if (target_actuator == "heater") { 
    current_red_light = doc_rec["e"][0]["v"].as<bool>(); 
    digitalWrite(LED_PIN, current_red_light ? HIGH : LOW); 
    Serial.println("Stato Heater aggiornato: " + String(current_red_light));
  }
  else if (target_actuator == "green_lights") { 
    current_green_light = doc_rec["e"][0]["v"].as<bool>(); 
    digitalWrite(GLED_PIN, current_green_light ? HIGH : LOW); 
  }
  else if (target_actuator == "fan") {
    float raw_v = doc_rec["e"][0]["v"].as<float>(); 
    current_fan_percent = (int)raw_v;
    analogWrite(FAN_PIN, map(current_fan_percent, 0, 100, 0, 255));
    Serial.println("Duty-cycle ventola aggiornato: " + String(current_fan_percent) + "%");
  }
  else if (target_actuator == "lcd") {
    String text = doc_rec["e"][0]["v"].as<String>();
    lcd.clear(); lcd.setCursor(0, 0); lcd.print(text); 
  }
}

void reconnect() {
  while (!mqtt_client.connected()) {
    String client_id = "ArduinoEdge-" + String(random(0xffff), HEX);
    if (mqtt_client.connect(client_id.c_str())) {
      Serial.println("MQTT Connesso con successo!");
      String sub_topic = BASE_TOPIC + "+/config";
      mqtt_client.subscribe(sub_topic.c_str());
    } else {
      delay(5000);
    }
  }
}
