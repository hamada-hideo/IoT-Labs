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

const char* catalog_address = SECRET_CATALOG_IP; 
int catalog_port = 8080; 

String broker_address = "";
int broker_port = 1883;

const String NODE_ID = SECRET_NODE_ID; 
const String BASE_TOPIC = "/tiot/group12/smart_home/" + NODE_ID + "/"; 
const String REGISTRATION_URL = "/catalog/devices";
const String TELEMETRY_TOPIC = "/tiot/group12/sensors/telemetry";

WiFiClient wifi_mqtt; 
WiFiClient wifi_http; 
PubSubClient mqtt_client(wifi_mqtt); 
HttpClient http_client = HttpClient(wifi_http, catalog_address, catalog_port);

StaticJsonDocument<512> doc_catalog_rx; 
StaticJsonDocument<512> doc_snd;  
StaticJsonDocument<512> doc_reg; 

LiquidCrystal_PCF8574 lcd(0x27);

const int GLED_PIN = 2; 
const int LED_PIN = 3;  
const int PIR_PIN = 4;
const int FAN_PIN = 5;  

unsigned long last_publish = 0;
unsigned long last_keepalive = 0; 
unsigned long last_mqtt_reconnect = 0; 

short sampleBuffer[256];
volatile int samplesRead = 0;
float current_noise_peak = 0.0;
float clapThresh = 30000.0; 
int nClaps = 2;
int clapInterval = 3000; 
int clapDuration = 200; 

bool current_green_light = false; 

const int RETRY_TIME = 5000;
const int REFRESH_LOOP_TIME = 5000;

struct Device {
  String id;
  bool is_actuator;
  String type;
  String unit;
  bool registered;
};

Device devices[] = {
  {"heater", true, "heater", "percent", false},
  {"green_lights", true, "green_lights", "bool", false},
  {"fan", true, "fan", "percent", false},
  {"lcd", true, "lcd", "string", false},
  {"temperature", false, "temperature", "Cel", false},
  {"motion", false, "motion", "bool", false},
  {"clap_sensor", false, "clap_sensor", "bool", false}
};

const int NUM_DEVICES = sizeof(devices) / sizeof(devices[0]);

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
  }
  Serial.println("WiFi Connesso!");

  IMU.begin();
  PDM.onReceive(onPDMdata);
  PDM.begin(1, 16000);

  http_client.setTimeout(3000);

  Serial.print("Cerco il Catalogo all'IP: ");
  Serial.println(catalog_address);

  http_client.get("/catalog/broker"); 
  int get_statusCode = http_client.responseStatusCode();
  String get_response = http_client.responseBody();
  http_client.stop();

  Serial.print("Risposta Broker GET: ");
  Serial.println(get_statusCode);

  while (get_statusCode != 200) {
    Serial.println("Catalog irraggiungibile, riprovo");
    delay(RETRY_TIME);
    http_client.get("/catalog/broker");
    get_statusCode = http_client.responseStatusCode();
    get_response = http_client.responseBody();
    http_client.stop();

    Serial.print("Risposta Broker GET: ");
    Serial.println(get_statusCode);
  }

  deserializeJson(doc_catalog_rx, get_response);
  broker_address = doc_catalog_rx["ip"].as<String>();
  broker_port = doc_catalog_rx["port"].as<int>();

  Serial.print("Broker IP Finale: ");
  Serial.println(broker_address);

  mqtt_client.setServer(broker_address.c_str(), broker_port);
  mqtt_client.setBufferSize(512); 
  mqtt_client.setCallback(callback);
}

void loop() {
  if (!mqtt_client.connected()) {
    if (millis() - last_mqtt_reconnect > 5000 || last_mqtt_reconnect == 0) {
      last_mqtt_reconnect = millis();
      String client_id = "ArduinoEdge-" + String(random(0xffff), HEX);
      if (mqtt_client.connect(client_id.c_str())) {
        Serial.println(">>> MQTT CONNESSO CON SUCCESSO! <<<");
        String sub_topic = BASE_TOPIC + "+/config";
        mqtt_client.subscribe(sub_topic.c_str());
      }
    }
  } else {
    mqtt_client.loop(); 
  }

  if (millis() - last_keepalive > REFRESH_LOOP_TIME) {
    for(int i = 0; i < NUM_DEVICES; i++) {
      register_refresh_device(i);
    }
    Serial.println("[APP] Keep-Alive REST inviato in background.");
    last_keepalive = millis();
  }

  // --- LOGICA MICROFONO BLINDATA ANTI-FREEZE ---
  if (samplesRead) {
    noInterrupts();
    int currentSamples = samplesRead;
    if (currentSamples > 256) currentSamples = 256; // Sicurezza buffer
    short localBuffer[256];
    memcpy(localBuffer, sampleBuffer, currentSamples * 2); 
    samplesRead = 0; 
    interrupts(); 

    static int k = 0; 
    static unsigned long begTime = 0;
    static unsigned long lastTime = millis(); 
    bool clapDetected = false;

    for (int i = 0; i < currentSamples; i++) {
      int a = abs(localBuffer[i]); 
      if (a > current_noise_peak) current_noise_peak = a;

      if(a > clapThresh && (millis() - lastTime) > clapDuration) {
        
        // IL FIX: Se è passato troppo tempo da un vecchio rumore a caso, si resetta!
        if (k > 0 && (millis() - begTime) > clapInterval) {
          k = 0;
        }

        if(k == 0) {
          begTime = millis();
        }
        
        k++;
        lastTime = millis();

        if(k == nClaps) {
          clapDetected = true; 
          k = 0; // Reset pulito post-attivazione
        }
      }
    }

    if (clapDetected) {
      StaticJsonDocument<128> doc_event;
      doc_event["bn"] = BASE_TOPIC;
      JsonArray ev_arr = doc_event.createNestedArray("e");
      JsonObject ev_obj = ev_arr.createNestedObject();
      ev_obj["n"] = "noise_event"; ev_obj["v"] = true; ev_obj["u"] = "bool"; ev_obj["t"] = millis() / 1000.0;
      String event_output; serializeJson(doc_event, event_output);
      
      if (mqtt_client.connected()) {
        mqtt_client.publish(TELEMETRY_TOPIC.c_str(), event_output.c_str());
        Serial.println("\n[APP] --- Clap Inviato a Python! ---");
      }
    }
  }

  if (millis() - last_publish > 10000) { 
    int raw_temp = 25; 
    if (IMU.temperatureAvailable()) IMU.readTemperature(raw_temp);
    
    doc_snd.clear(); doc_snd["bn"] = BASE_TOPIC; 
    JsonArray events = doc_snd.createNestedArray("e");

    JsonObject ev_temp = events.createNestedObject();
    ev_temp["n"] = "temperature"; ev_temp["v"] = (float)raw_temp; ev_temp["u"] = "Cel"; ev_temp["t"] = millis() / 1000.0;
    
    JsonObject ev_motion = events.createNestedObject();
    ev_motion["n"] = "motion"; ev_motion["v"] = (bool)digitalRead(PIR_PIN); ev_motion["u"] = "bool"; ev_motion["t"] = millis() / 1000.0;

    String output; serializeJson(doc_snd, output); 
    if (mqtt_client.connected()) {
        mqtt_client.publish(TELEMETRY_TOPIC.c_str(), output.c_str()); 
        Serial.println("[APP] Telemetria ambientale inviata.");
    }
    last_publish = millis();
  }
}

void onPDMdata() {
  int bytesAvailable = PDM.available();
  PDM.read(sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;
}

void callback(char* topic, byte* payload, unsigned int length) { 
  Serial.print("[MQTT RX] Ricevuto comando su: ");
  Serial.println(topic);

  StaticJsonDocument<512> doc_rec; 
  DeserializationError err = deserializeJson(doc_rec, payload, length); 
  if (err) return; 

  String topicStr = String(topic);
  topicStr.replace(BASE_TOPIC, ""); topicStr.replace("/config", ""); 
  String target_actuator = topicStr; 

  if (target_actuator == "heater") { 
    int current_heater_percent = doc_rec["e"][0]["v"].as<int>(); 
    analogWrite(LED_PIN, map(current_heater_percent, 0, 100, 0, 255)); 
  }
  else if (target_actuator == "green_lights") { 
    String resource_name = doc_rec["e"][0]["n"].as<String>();
    if (resource_name.endsWith("_toggle")) {
      current_green_light = !current_green_light; 
      Serial.println("[AZIONE] Eseguito TOGGLE su Luce Verde!");
    } else {
      current_green_light = doc_rec["e"][0]["v"].as<bool>(); 
    }
    digitalWrite(GLED_PIN, current_green_light ? HIGH : LOW); 
  }
  else if (target_actuator == "fan") {
    int current_fan_percent = doc_rec["e"][0]["v"].as<int>(); 
    analogWrite(FAN_PIN, map(current_fan_percent, 0, 100, 0, 255));
  }
  else if (target_actuator == "lcd") {
    String text = doc_rec["e"][0]["v"].as<String>();
    lcd.clear(); 
    int splitIndex = text.indexOf('|');
    
    if (splitIndex != -1) {
      String r1 = text.substring(0, splitIndex);
      String r2 = text.substring(splitIndex + 1);
      if(r1.length() > 16) r1 = r1.substring(0, 16);
      if(r2.length() > 16) r2 = r2.substring(0, 16);
      lcd.setCursor(0, 0); lcd.print(r1); 
      lcd.setCursor(0, 1); lcd.print(r2); 
    } else {
      if(text.length() > 16) text = text.substring(0, 16);
      lcd.setCursor(0, 0); lcd.print(text); 
    }
  }
}

void register_refresh_device(int i) {
  if (!devices[i].registered) {
    if (register_device(i)) {
      devices[i].registered = true;
    }
  } else {
    if (!refresh_device(i)) {
      devices[i].registered = false;
    }
  }
}

bool register_device(int i) {
  doc_reg.clear();
  String dev_id = NODE_ID + "/" + devices[i].id;
  doc_reg["id"] = dev_id;
  doc_reg["description"] = "Arduino actuator " + dev_id;
  JsonObject res = doc_reg.createNestedObject("resources");
  res["type"] = devices[i].type; 
  res["unit"] = devices[i].unit;
  JsonObject mqtt_info = doc_reg.createNestedObject("mqtt");

  if (devices[i].is_actuator) {
    mqtt_info["command_topic"] = BASE_TOPIC + dev_id + "/config";
    mqtt_info["feedback_topic"] = BASE_TOPIC + dev_id + "/state";
    if (i != 3) {
      mqtt_info["logger_topic"] = mqtt_info["command_topic"]; // do not log every lcd screeen change
    }
  } else {
    mqtt_info["pub_topic"] = TELEMETRY_TOPIC;
    mqtt_info["logger_topic"] = TELEMETRY_TOPIC;
  }

  String reg_body; serializeJson(doc_reg, reg_body);
  http_client.post(REGISTRATION_URL, "application/json", reg_body);
  int postCode = http_client.responseStatusCode(); 
  http_client.responseBody(); 
  http_client.stop();
  delay(100);   

  return postCode == 200;
}

bool refresh_device(int i) {
  String dev_id = NODE_ID + "/" + devices[i].id;
  http_client.put(REGISTRATION_URL + "/" + dev_id, "application/json", "{}");
  int putCode = http_client.responseStatusCode(); 
  http_client.responseBody(); 
  http_client.stop(); 
  delay(150); 
  return putCode == 200;
}
