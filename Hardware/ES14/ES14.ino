#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Arduino_LSM6DSOX.h> 
#include <PDM.h>              
#include "arduino_secrets.h" 
#include <LiquidCrystal_PCF8574.h> 

// --- CONFIGURAZIONI DI RETE ---
char ssid[] = SECRET_SSID; 
char pass[] = SECRET_PASS; 

// IP DEL TUO PC 
const char* catalog_address = "192.168.1.100"; 
int catalog_port = 8080; 
const String catalog_endpoint = "/catalog/devices";

// Broker MQTT
const char* broker_address = "broker.emqx.io";
int broker_port = 1883; 
const String base_topic = "/tiot/group12"; 
const String device_id = "arduino_living_room";

// --- INIZIALIZZAZIONE COMPONENTI ---
WiFiClient wifi; 
PubSubClient mqtt_client(wifi); 
HttpClient http_client = HttpClient(wifi, catalog_address, catalog_port);

StaticJsonDocument<384> doc_snd; 
StaticJsonDocument<256> doc_rec; 
StaticJsonDocument<256> doc_reg; 

LiquidCrystal_PCF8574 lcd(0x27);

// Pin hardware del tuo circuito
const int LED_PIN = 3;
const int PIR_PIN = 4;
const int FAN_PIN = 5; 

// --- VARIABILI GLOBALI ---
unsigned long last_publish = 0;
short sampleBuffer[256];
volatile int samplesRead = 0;
float current_noise_peak = 0.0;

// KILL-SWITCH Variabile di stato del sistema
bool isRunning = true; 

// Dichiarazione funzioni
void reconnect();
void onPDMdata();

void setup() {
  Serial.begin(9600);
  
  pinMode(FAN_PIN, OUTPUT); 
  pinMode(LED_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  
  lcd.begin(16, 2);
  lcd.setBacklight(255);
  lcd.clear();
  lcd.print("Connessione...");

  // Connessione WiFi
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    delay(1000);
    Serial.println("Tentativo di connessione al WiFi...");
  }
  lcd.clear();
  lcd.print("WiFi Connesso!");
  Serial.println("WiFi Connesso con successo!");

  // Inizializzazione Sensori Interni
  if (!IMU.begin()) {
    Serial.println("Errore IMU!");
  }
  PDM.onReceive(onPDMdata);
  PDM.begin(1, 16000);

  // Registrazione Device via REST
  Serial.println("Avvio registrazione REST al Catalogo...");
  
  doc_reg.clear();
  doc_reg["id"] = device_id;
  doc_reg["description"] = "Arduino RP2040 Edge Node (Kill-Switch ready)";
  JsonObject resources = doc_reg.createNestedObject("resources");
  resources["temperature"] = "Cel";
  resources["motion"] = "bool";
  resources["noise"] = "mV";

  String reg_body;
  serializeJson(doc_reg, reg_body);
  http_client.post(catalog_endpoint.c_str(), "application/json", reg_body);
  
  if (http_client.responseStatusCode() == 200) {
    lcd.clear(); lcd.print("Reg. REST OK!"); delay(1000);
  } else {
    Serial.println("Errore nella registrazione REST al Catalogo.");
  }

  // 4. Configurazione MQTT
  mqtt_client.setServer(broker_address, broker_port);
  mqtt_client.setCallback(callback);
}

void loop() {
  // MQTT deve sempre girare per intercettare i comandi
  if (!mqtt_client.connected()) {
    reconnect(); 
  }
  mqtt_client.loop(); 

  // Calcolo picco rumore in background
  if (samplesRead) {
    for (int i = 0; i < samplesRead; i++) {
      if (abs(sampleBuffer[i]) > current_noise_peak) current_noise_peak = abs(sampleBuffer[i]);
    }
    samplesRead = 0;
  }

  // KILL-SWITCH Se il sistema è in pausa, salta la lettura e l'invio
  if (!isRunning) {
    return; 
  }

  // LETTURA E PUBBLICAZIONE 
  if (millis() - last_publish > 10000) { 
    
    // Temperatura
    int raw_temp = 25; 
    if (IMU.temperatureAvailable()) IMU.readTemperature(raw_temp);
    float temp_val = (float)raw_temp; 

    // Movimento
    int motion_val = digitalRead(PIR_PIN);
    
    // Rumore
    float noise_val = current_noise_peak;
    current_noise_peak = 0.0; 

    // Timestamp
    float current_time_sec = millis() / 1000.0; 

    // Costruzione JSON SenML
    doc_snd.clear(); 
    doc_snd["bn"] = "smart_home/living_room/"; 
    JsonArray events = doc_snd.createNestedArray("e");

    JsonObject ev_temp = events.createNestedObject();
    ev_temp["n"] = "temperature"; ev_temp["v"] = temp_val; ev_temp["u"] = "Cel"; ev_temp["t"] = current_time_sec;

    JsonObject ev_motion = events.createNestedObject();
    ev_motion["n"] = "motion"; ev_motion["v"] = (bool)motion_val; ev_motion["u"] = "bool"; ev_motion["t"] = current_time_sec;

    JsonObject ev_noise = events.createNestedObject();
    ev_noise["n"] = "noise"; ev_noise["v"] = noise_val; ev_noise["u"] = "mV"; ev_noise["t"] = current_time_sec;

    String output; 
    serializeJson(doc_snd, output); 
    
    // Pubblicazione MQTT
    String pub_topic = base_topic + "/sensors/telemetry";
    mqtt_client.publish(pub_topic.c_str(), output.c_str()); 
    
    // [DEBUG RIPRISTINATO] Stampa il JSON grezzo sul terminale
    Serial.println("Dati SenML inviati: " + output);
    
    last_publish = millis();
  }
}

// Interruzione hardware per il microfono PDM
void onPDMdata() {
  int bytesAvailable = PDM.available();
  PDM.read(sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;
}

// Callback per la ricezione comandi da Python/Mosquitto
void callback(char* topic, byte* payload, unsigned int length) { 
  DeserializationError err = deserializeJson(doc_rec, (char*) payload); 
  if (err) return; 

  String n_field = doc_rec["e"][0]["n"].as<String>(); 

  // [KILL-SWITCH] Gestione remota accensione/spegnimento
  if (n_field.endsWith("system")) {
    isRunning = doc_rec["e"][0]["v"].as<bool>();
    
    if (!isRunning) {
      digitalWrite(LED_PIN, LOW);
      analogWrite(FAN_PIN, 0);
      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("=== IN PAUSA ===");
      Serial.println("\n[SISTEMA IN PAUSA] Attuatori spenti. Invio dati interrotto.");
    } else {
      lcd.clear();
      lcd.print("SISTEMA ATTIVO");
      Serial.println("\n[SISTEMA RIATTIVATO] Ripresa operazioni normali.");
    }
    return;
  }

  // Se è in pausa ignora gli altri comandi
  if (!isRunning) return;

  // Gestione Attuatori Standard
  if (n_field.endsWith("lights")) { 
    bool state = doc_rec["e"][0]["v"].as<bool>(); 
    digitalWrite(LED_PIN, state ? HIGH : LOW);
    Serial.println(state ? "Comando RX: Luce ACCESA" : "Comando RX: Luce SPENTA");
  }
  else if (n_field.endsWith("fan")) {
    int ac_speed_percent = doc_rec["e"][0]["v"].as<int>();
    int pwm_val = map(ac_speed_percent, 0, 100, 0, 255);
    analogWrite(FAN_PIN, pwm_val); 
    Serial.print("Comando RX: Ventola al "); Serial.print(ac_speed_percent); Serial.println("%");
  }
  else if (n_field.endsWith("lcd")) {
    String text = doc_rec["e"][0]["v"].as<String>();
    lcd.clear(); lcd.setCursor(0, 0); lcd.print(text); 
  }
}

// Funzione riconnessione automatica MQTT
void reconnect() {
  while (!mqtt_client.connected()) {
    Serial.println("Connessione MQTT al Broker in corso...");
    String client_id = "ArduinoClient-" + String(random(0xffff), HEX);
    if (mqtt_client.connect(client_id.c_str())) {
      Serial.println("MQTT Connesso!");
      String sub_topic = base_topic + "/actuators/commands";
      mqtt_client.subscribe(sub_topic.c_str());
    } else {
      Serial.println("Connessione fallita, nuovo tentativo tra 5 secondi...");
      delay(5000);
    }
  }
}