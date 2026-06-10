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

// Indirizzo del Catalogo REST
const char* catalog_address = "192.168.1.100"; 
int catalog_port = 8080; 

// Stringhe dinamiche che verranno riempite tramite la GET REST
String broker_address = "";
int broker_port = 1883;

const String base_topic = "/tiot/group12"; 
const String device_id = "arduino_living_room";

WiFiClient wifi; 
PubSubClient mqtt_client(wifi); 
HttpClient http_client = HttpClient(wifi, catalog_address, catalog_port);

// Buffer allocati correttamente per evitare overflow
StaticJsonDocument<512> doc_catalog_rx; // Più grande per ospitare la risposta del catalogo
StaticJsonDocument<384> doc_snd; 
StaticJsonDocument<256> doc_rec; 
StaticJsonDocument<256> doc_reg; 

LiquidCrystal_PCF8574 lcd(0x27);

const int GLED_PIN = 2; 
const int LED_PIN = 3;  
const int PIR_PIN = 4;
const int FAN_PIN = 5; 

unsigned long last_publish = 0;
short sampleBuffer[256];
volatile int samplesRead = 0;
float current_noise_peak = 0.0;

// Configurazione algoritmi audio locali (Edge Computing)
float clapThresh = 30000.0; 
int nClaps = 2;
int clapInterval = 3000; 
int clapDuration = 200; 

bool isRunning = true; 

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

  // Connessione Wi-Fi
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connessione al WiFi...");
  }
  Serial.println("WiFi Connesso!");

  if (!IMU.begin()) Serial.println("Errore IMU!");
  PDM.onReceive(onPDMdata);
  PDM.begin(1, 16000);

  // RECUPERO INFORMAZIONI BROKER VIA REST GET 
  Serial.println("Recupero info broker dal Catalogo...");
  http_client.get("/catalog"); // Esegue la GET all'endpoint principale del catalogo
  
  int get_statusCode = http_client.responseStatusCode();
  String get_response = http_client.responseBody();

  if (get_statusCode == 200) {
    DeserializationError err = deserializeJson(doc_catalog_rx, get_response);
    if (!err) {
      // Estrazione dinamica dei parametri del broker inviati dal catalogo
      broker_address = doc_catalog_rx["broker_address"].as<String>();
      broker_port = doc_catalog_rx["broker_port"].as<int>();
      
      Serial.print("[REST GET] Broker ottenuto: "); Serial.print(broker_address);
      Serial.print(":"); Serial.println(broker_port);
    } else {
      Serial.println("Errore nel parsing del JSON del Catalogo. Uso fallback.");
      broker_address = "broker.emqx.io"; // Fallback di sicurezza
    }
  } else {
    Serial.println("Impossibile connettersi al Catalogo via REST. Uso fallback.");
    broker_address = "broker.emqx.io";
  }

  // REGISTRAZIONE DEL DEVICE VIA REST POST
  doc_reg.clear();
  doc_reg["id"] = device_id;
  doc_reg["description"] = "Arduino RP2040 Edge Node definitivo";
  JsonObject resources = doc_reg.createNestedObject("resources");
  resources["temperature"] = "Cel";
  resources["motion"] = "bool";
  resources["noise"] = "mV";

  String reg_body;
  serializeJson(doc_reg, reg_body);
  http_client.post("/catalog/devices", "application/json", reg_body);
  
  if (http_client.responseStatusCode() == 200) {
    lcd.clear(); lcd.print("Reg. REST OK!"); delay(1000);
  }

  // CONFIGURAZIONE DINAMICA CLIENT MQTT
  mqtt_client.setServer(broker_address.c_str(), broker_port);
  mqtt_client.setCallback(callback);
}

void loop() {
  if (!mqtt_client.connected()) {
    reconnect(); 
  }
  mqtt_client.loop(); 

  // Analisi del segnale audio locale ad alta frequenza
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
          // Generazione e pubblicazione dell'evento leggero asincrono "una tantum"
          StaticJsonDocument<256> doc_event;
          doc_event["bn"] = "smart_home/living_room/";
          JsonArray ev_arr = doc_event.createNestedArray("e");
          JsonObject ev_obj = ev_arr.createNestedObject();
          ev_obj["n"] = "noise_event";
          ev_obj["v"] = true;
          ev_obj["u"] = "bool";
          ev_obj["t"] = millis() / 1000.0;

          String event_output;
          serializeJson(doc_event, event_output);
          String pub_topic = base_topic + "/sensors/telemetry";
          mqtt_client.publish(pub_topic.c_str(), event_output.c_str());
          
          Serial.println("[EDGE EVENT] Doppio applauso! Notifica inviata a Python.");
          k = 0; 
        }
      }
    }
    samplesRead = 0;
  }

  if (!isRunning) return; 

  // Pubblicazione standard periodica
  if (millis() - last_publish > 10000) { 
    int raw_temp = 25; 
    if (IMU.temperatureAvailable()) IMU.readTemperature(raw_temp);
    float temp_val = (float)raw_temp; 

    int motion_val = digitalRead(PIR_PIN);
    float noise_val = current_noise_peak;
    current_noise_peak = 0.0; 

    doc_snd.clear(); 
    doc_snd["bn"] = "smart_home/living_room/"; 
    JsonArray events = doc_snd.createNestedArray("e");

    JsonObject ev_temp = events.createNestedObject();
    ev_temp["n"] = "temperature"; ev_temp["v"] = temp_val; ev_temp["u"] = "Cel"; ev_temp["t"] = millis() / 1000.0;

    JsonObject ev_motion = events.createNestedObject();
    ev_motion["n"] = "motion"; ev_motion["v"] = (bool)motion_val; ev_motion["u"] = "bool"; ev_motion["t"] = millis() / 1000.0;

    JsonObject ev_noise = events.createNestedObject();
    ev_noise["n"] = "noise"; ev_noise["v"] = noise_val; ev_noise["u"] = "mV"; ev_noise["t"] = millis() / 1000.0;

    String output; 
    serializeJson(doc_snd, output); 
    String pub_topic = base_topic + "/sensors/telemetry";
    mqtt_client.publish(pub_topic.c_str(), output.c_str()); 
    
    Serial.println("Dati SenML inviati: " + output);
    last_publish = millis();
  }
}

void onPDMdata() {
  int bytesAvailable = PDM.available();
  PDM.read(sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;
}

// Ricezione comandi ed esecuzione passiva cieca
void callback(char* topic, byte* payload, unsigned int length) { 
  DeserializationError err = deserializeJson(doc_rec, (char*) payload); 
  if (err) return; 

  String n_field = doc_rec["e"][0]["n"].as<String>(); 

  if (n_field.endsWith("system")) {
    isRunning = doc_rec["e"][0]["v"].as<bool>();
    if (!isRunning) {
      digitalWrite(LED_PIN, LOW); digitalWrite(GLED_PIN, LOW); analogWrite(FAN_PIN, 0);
      lcd.clear(); lcd.print("=== IN PAUSA ===");
    } else {
      lcd.clear(); lcd.print("SISTEMA ATTIVO");
    }
    return;
  }

  if (!isRunning) return;

  if (n_field.endsWith("lights")) { 
    bool state = doc_rec["e"][0]["v"].as<bool>(); 
    digitalWrite(LED_PIN, state ? HIGH : LOW); // Attuazione cieca
  }
  else if (n_field.endsWith("green_lights")) { 
    bool state = doc_rec["e"][0]["v"].as<bool>(); 
    digitalWrite(GLED_PIN, state ? HIGH : LOW); // Attuazione cieca del LED verde da comando Python
  }
  else if (n_field.endsWith("fan")) {
    int ac_speed_percent = doc_rec["e"][0]["v"].as<int>();
    int pwm_val = map(ac_speed_percent, 0, 100, 0, 255);
    analogWrite(FAN_PIN, pwm_val); // Attuazione cieca ventola
  }
  else if (n_field.endsWith("lcd")) {
    String text = doc_rec["e"][0]["v"].as<String>();
    lcd.clear(); lcd.setCursor(0, 0); lcd.print(text); // Stampa cieca testo da Python
  }
}

void reconnect() {
  while (!mqtt_client.connected()) {
    String client_id = "ArduinoClient-" + String(random(0xffff), HEX);
    if (mqtt_client.connect(client_id.c_str())) {
      String sub_topic = base_topic + "/actuators/commands";
      mqtt_client.subscribe(sub_topic.c_str());
    } else {
      delay(5000);
    }
  }
}
