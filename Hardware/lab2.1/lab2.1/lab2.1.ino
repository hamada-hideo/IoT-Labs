#include <Wire.h>
#include <LiquidCrystal_PCF8574.h>
#include <Arduino_LSM6DSOX.h>

// --- Pin Definitions ---
const int FAN_PIN = 5;      // DC Motor (Air Conditioning)
const int HEATER_PIN = 3;   // Red LED (Heating)
const int PIR_PIN = 4;      // PIR Motion Sensor
const int MIC_PIN = A1;     // Analog Microphone Sensor

LiquidCrystal_PCF8574 lcd(0x27); // Standard I2C address for the LCD

// --- Timeouts & Thresholds ---
const unsigned long TIMEOUT_PIR = 30UL * 60UL * 1000UL;   // 30 minutes
const unsigned long TIMEOUT_SOUND = 60UL * 60UL * 1000UL; // 60 minutes
const unsigned long SOUND_INTERVAL = 10UL * 60UL * 1000UL;// 10 minutes window
const int N_SOUND_EVENTS = 10;
// Note: Calibrate SOUND_THRESHOLD so it ignores the fan noise but catches human sounds
const int SOUND_THRESHOLD = 600; 

// --- Set-points: Presence Detected (Comfort) ---
float ac_min_pres = 25.0;
float ac_max_pres = 30.0;
float ht_min_pres = 15.0;
float ht_max_pres = 20.0;

// --- Set-points: No Presence (Eco) ---
float ac_min_eco = 28.0;
float ac_max_eco = 33.0;
float ht_min_eco = 12.0;
float ht_max_eco = 17.0;

// --- State Variables ---
float current_temp = 20.0;

// Presence variables
bool pir_presence = false;
bool mic_presence = false;
bool total_presence = false;

unsigned long last_pir_motion_time = 0;
unsigned long last_valid_mic_time = 0;

// Microphone debouncing and windowing variables
int sound_events_count = 0;
unsigned long first_sound_event_time = 0;
unsigned long last_sound_spike_time = 0;

// Output variables
int ac_percent = 0;
int ht_percent = 0;

// LCD & Serial management
unsigned long last_screen_switch = 0;
bool show_screen_1 = true;
String inputString = "";

void setup() {
  Serial.begin(9600);

  // Pin Initialization
  pinMode(FAN_PIN, OUTPUT);
  pinMode(HEATER_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  // MIC_PIN is analog, no pinMode needed

  analogWrite(FAN_PIN, 0);
  analogWrite(HEATER_PIN, 0);

  // LCD Initialization
  lcd.begin(16, 2);
  lcd.setBacklight(255);
  lcd.clear();
  lcd.print("Smart Home Local");

  // IMU Initialization
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }
  
  delay(2000);
  lcd.clear();
}

void loop() {
  unsigned long now = millis();

  // 1. Temperature Reading (Internal Sensor)
  if (IMU.temperatureAvailable()) {
    int temp_raw = 0; // Temporary int variable for the sensor
    IMU.readTemperature(temp_raw);
    current_temp = temp_raw; // Assign to the global float variable
  }

  // 2. PIR Motion Reading & Timeout
  if (digitalRead(PIR_PIN) == HIGH) {
    last_pir_motion_time = now;
    pir_presence = true;
  }
  if (pir_presence && (now - last_pir_motion_time >= TIMEOUT_PIR)) {
    pir_presence = false;
  }

  // 3. Microphone Reading & Event Window Logic
  int mic_value = analogRead(MIC_PIN);
  
  // Basic debouncing: wait at least 200ms between sound spikes so one clap isn't counted 10 times
  if (mic_value > SOUND_THRESHOLD && (now - last_sound_spike_time > 200)) {
    last_sound_spike_time = now;
    
    if (sound_events_count == 0) {
      first_sound_event_time = now; // Start of the window
    }
    
    sound_events_count++;
    
    if (sound_events_count >= N_SOUND_EVENTS) {
      mic_presence = true;
      last_valid_mic_time = now;
      sound_events_count = 0; // Reset counter after confirming presence
    }
  }

  // Reset sound counter if the time window (10 mins) expires before reaching n_sound_events
  if (sound_events_count > 0 && (now - first_sound_event_time >= SOUND_INTERVAL)) {
    sound_events_count = 0;
  }

  // Mic timeout logic (60 mins)
  if (mic_presence && (now - last_valid_mic_time >= TIMEOUT_SOUND)) {
    mic_presence = false;
  }

  // 4. Combine Sensor Measurements (OR logic)
  total_presence = pir_presence || mic_presence;

  // 5. Automatic Adjustment of Set-points (Comfort vs Eco)
  float ac_min = total_presence ? ac_min_pres : ac_min_eco;
  float ac_max = total_presence ? ac_max_pres : ac_max_eco;
  float ht_min = total_presence ? ht_min_pres : ht_min_eco;
  float ht_max = total_presence ? ht_max_pres : ht_max_eco;

  // 6. Proportional Logic for Air Conditioning
  if (current_temp <= ac_min) {
    ac_percent = 0;
  } else if (current_temp >= ac_max) {
    ac_percent = 100;
  } else {
    ac_percent = map((long)(current_temp * 10), (long)(ac_min * 10), (long)(ac_max * 10), 0, 100);
  }
  analogWrite(FAN_
