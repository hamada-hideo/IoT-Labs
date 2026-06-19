#include <Scheduler.h>
#include <Wire.h>
#include <LiquidCrystal_PCF8574.h>
#include <Arduino_LSM6DSOX.h>

// --- Pin Definitions ---
const int FAN_PIN = 5;      // DC Motor (Air Conditioning)
const int HEATER_PIN = 3;   // Red LED (Heating)
const int PIR_PIN = 4;      // PIR Motion Sensor
const int MIC_PIN = A1;     // Analog Microphone Sensor

LiquidCrystal_PCF8574 lcd(0x27);

// --- Timeouts & Thresholds ---
const unsigned long TIMEOUT_PIR = 30UL * 60UL * 1000UL;   // 30 minutes
const unsigned long TIMEOUT_SOUND = 60UL * 60UL * 1000UL; // 60 minutes
const unsigned long SOUND_INTERVAL = 10UL * 60UL * 1000UL;// 10 minutes window
const int N_SOUND_EVENTS = 10;
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

// --- SHARED STATE VARIABLES (Volatile for Scheduler Thread Safety) ---
volatile float v_current_temp = 20.0;
volatile bool pir_presence = false;
volatile bool mic_presence = false;

// Output states for LCD
volatile int ac_percent = 0;
volatile int ht_percent = 0;
volatile bool total_presence = false;

// Display and Serial Variables
int currentScreen = 0;
String inputString = "";

void setup() {
  Serial.begin(9600);
  while (!Serial);

  Serial.println("Smart Home Scheduler Version Starting...");

  // Pin Initialization
  pinMode(FAN_PIN, OUTPUT);
  pinMode(HEATER_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);

  analogWrite(FAN_PIN, 0);
  analogWrite(HEATER_PIN, 0);

  // LCD Initialization
  lcd.begin(16, 2);
  lcd.setBacklight(255);
  lcd.clear();
  lcd.print("Smart Home Setup");

  // IMU Initialization
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }
  
  delay(1000);
  lcd.clear();

  // --- Start Scheduler Threads ---
  Scheduler.startLoop(loopTemp);
  Scheduler.startLoop(loopPIR);
  Scheduler.startLoop(loopMic);
}

// =========================================
// MAIN LOOP: Actuators, Display, and Serial
// =========================================
void loop() {
  // 1. Safely read shared states
  noInterrupts();
  bool pp = pir_presence;
  bool mp = mic_presence;
  float current_temp = v_current_temp;
  interrupts();

  // 2. Combine Presence
  bool presence = pp || mp;
  
  noInterrupts();
  total_presence = presence;
  interrupts();

  // 3. Set-points selection (Comfort vs Eco)
  float ac_min = presence ? ac_min_pres : ac_min_eco;
  float ac_max = presence ? ac_max_pres : ac_max_eco;
  float ht_min = presence ? ht_min_pres : ht_min_eco;
  float ht_max = presence ? ht_max_pres : ht_max_eco;

  // 4. Proportional Control Logic
  int local_ac_percent = 0;
  if (current_temp <= ac_min) local_ac_percent = 0;
  else if (current_temp >= ac_max) local_ac_percent = 100;
  else local_ac_percent = map((long)(current_temp * 10), (long)(ac_min * 10), (long)(ac_max * 10), 0, 100);
  
  analogWrite(FAN_PIN, map(local_ac_percent, 0, 100, 0, 255));

  int local_ht_percent = 0;
  if (current_temp >= ht_max) local_ht_percent = 0;
  else if (current_temp <= ht_min) local_ht_percent = 100;
  else local_ht_percent = map((long)(current_temp * 10), (long)(ht_min * 10), (long)(ht_max * 10), 100, 0);
  
  analogWrite(HEATER_PIN, map(local_ht_percent, 0, 100, 0, 255));

  // Update volatile percents for LCD safely
  noInterrupts();
  ac_percent = local_ac_percent;
  ht_percent = local_ht_percent;
  interrupts();

  // 5. LCD Update Logic (cycles every 5s)
  static unsigned long lastScreenSwitch = 0;
  if (millis() - lastScreenSwitch > 5000) {
    lastScreenSwitch = millis();
    currentScreen = (currentScreen + 1) % 2; // Toggles between 0 and 1
    lcd.clear();
    
    lcd.setCursor(0, 0);
    if (currentScreen == 0) {
      lcd.print("T:"); lcd.print(current_temp, 1);
      lcd.print(" Pres:"); lcd.print(presence ? "1" : "0");
      lcd.setCursor(0, 1);
      lcd.print("AC:"); lcd.print(local_ac_percent); lcd.print("% HT:"); lcd.print(local_ht_percent); lcd.print("%");
    } else {
      lcd.print("AC m:"); lcd.print(ac_min, 1); lcd.print(" M:"); lcd.print(ac_max, 1);
      lcd.setCursor(0, 1);
      lcd.print("HT m:"); lcd.print(ht_min, 1); lcd.print(" M:"); lcd.print(ht_max, 1);
    }
  }

  // 6. Serial Parsing Logic
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      processSerialCommand(inputString);
      inputString = "";
    } else if (inChar != '\r') {
      inputString += inChar;
    }
  }
  
  yield(); // Hands control back to the scheduler
}

// =========================================
// THREAD 1: Temperature Sensor Logic
// =========================================
void loopTemp() {
  static unsigned long lastReadTime = 0;

  if (millis() - lastReadTime >= 1000) { // Reads every 1 second
    lastReadTime = millis();

    if (IMU.temperatureAvailable()) {
      int temp_raw = 0;
      IMU.readTemperature(temp_raw);
      
      noInterrupts();
      v_current_temp = (float)temp_raw;
      interrupts();
    }
  }
  yield(); // Hands control back
}

// =========================================
// THREAD 2: PIR Motion Sensor Logic
// =========================================
void loopPIR() {
  static unsigned long lastMotionTime = 0;
  
  int pirState = digitalRead(PIR_PIN);

  if (pirState == HIGH) {
    lastMotionTime = millis();
    noInterrupts();
    pir_presence = true;
    interrupts();
  }

  noInterrupts();
  bool local_pir = pir_presence;
  interrupts();

  if (local_pir && (millis() - lastMotionTime >= TIMEOUT_PIR)) {
    noInterrupts();
    pir_presence = false;
    interrupts();
  }
  
  yield();
}

// =========================================
// THREAD 3: Analog Microphone Logic
// =========================================
void loopMic() {
  static int sound_events_count = 0;
  static unsigned long first_sound_event_time = 0;
  static unsigned long last_sound_spike_time = 0;
  static unsigned long last_valid_mic_time = 0;

  int mic_value = analogRead(MIC_PIN);
  unsigned long now = millis();

  // Spike detection with 200ms debounce
  if (mic_value > SOUND_THRESHOLD && (now - last_sound_spike_time > 200)) {
    last_sound_spike_time = now;
    
    if (sound_events_count == 0) {
      first_sound_event_time = now;
    }
    sound_events_count++;
    
    if (sound_events_count >= N_SOUND_EVENTS) {
      noInterrupts();
      mic_presence = true;
      interrupts();
      
      last_valid_mic_time = now;
      sound_events_count = 0; // Reset counter
    }
  }

  // Window timeout reset
  if (sound_events_count > 0 && (now - first_sound_event_time >= SOUND_INTERVAL)) {
    sound_events_count = 0;
  }

  // General presence timeout
  noInterrupts();
  bool local_mic = mic_presence;
  interrupts();

  if (local_mic && (now - last_valid_mic_time >= TIMEOUT_SOUND)) {
    noInterrupts();
    mic_presence = false;
    interrupts();
  }

  yield();
}

// =========================================
// UTILITY: Serial Command Processor
// =========================================
void processSerialCommand(String cmd) {
  cmd.trim();
  int separator = cmd.indexOf(':');
  if (separator == -1) return;

  String key = cmd.substring(0, separator);
  float val = cmd.substring(separator + 1).toFloat();

  if (key == "AC_MIN_PRES") ac_min_pres = val;
  else if (key == "AC_MAX_PRES") ac_max_pres = val;
  else if (key == "HT_MIN_PRES") ht_min_pres = val;
  else if (key == "HT_MAX_PRES") ht_max_pres = val;
  else if (key == "AC_MIN_ECO") ac_min_eco = val;
  else if (key == "AC_MAX_ECO") ac_max_eco = val;
  else if (key == "HT_MIN_ECO") ht_min_eco = val;
  else if (key == "HT_MAX_ECO") ht_max_eco = val;
  else {
    Serial.println("Unknown command.");
    return;
  }
  
  Serial.print("Updated ");
  Serial.print(key);
  Serial.print(" to ");
  Serial.println(val);
}