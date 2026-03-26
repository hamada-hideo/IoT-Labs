#include <PDM.h>
#include <Arduino_LSM6DSOX.h>
#include <Wire.h>
#include <LiquidCrystal_PCF8574.h>

// Inizializzazione Display LCD I2C all'indirizzo standard 0x27
LiquidCrystal_PCF8574 lcd(0x27);

// --- DEFINIZIONE PIN ---
const int FAN_PIN = 5;      
const int RLED_PIN = 2;     
const int PIR_PIN = 4;      

// --- SET-POINT DI TEMPERATURA ---
// Valori di comfort (presenza). NON sono 'const' perché li modifichiamo via Seriale (Punto h)
float TAC_min_pres = 25.0; 
float TAC_max_pres = 30.0;
float THT_max_pres = 20.0; 
float THT_min_pres = 15.0;

// Valori di risparmio energetico (assenza). Questi rimangono costanti.
const float TAC_min_abs = 28.0; 
const float TAC_max_abs = 33.0;
const float THT_max_abs = 17.0; 
const float THT_min_abs = 12.0;

// Variabili operative correnti per i set-point
float TAC_min;
float TAC_max;
float THT_max;
float THT_min;

// --- VARIABILI SENSORI ---
// Variabili PIR
volatile unsigned long lastMotionTime = 0;
const unsigned long timeout_pir = 30UL * 60UL * 1000UL; 
bool isPresencePIR = false;

// Variabili PDM (con array corretto)
volatile short sampleBuffer[255]; 
volatile int samplesRead = 0;

const int sound_threshold = 10000;
const int n_sound_events = 10;
const unsigned long sound_interval = 10UL * 60UL * 1000UL;
const unsigned long timeout_sound = 60UL * 60UL * 1000UL;
bool isPresenceSound = false;
int soundEventsCount = 0;
unsigned long firstEventTime = 0;
unsigned long lastSoundTime = 0;

// Variabile Combinata
bool isRoomOccupied = false;

// Variabili per Display
unsigned long lastDisplaySwitch = 0;
bool showScreen1 = true;

// Variabili globali per salvare l'output in percentuale (per il display)
int fanSpeedPercent = 0;
int heaterIntensityPercent = 0;

// ISR Sensore PIR
void checkPresence() {
  if (digitalRead(PIR_PIN) == HIGH) {
    lastMotionTime = millis();
  }
}

// ISR Microfono PDM
void onPDMdata() {
  int bytesAvailable = PDM.available();
  PDM.read((void*)sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;
}

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // Inizializzazione Pin
  pinMode(FAN_PIN, OUTPUT);
  pinMode(RLED_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);

  // Inizializzazione PIR
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), checkPresence, CHANGE);

  // Inizializzazione Microfono PDM
  PDM.onReceive(onPDMdata);
  if (!PDM.begin(1, 16000)) {
    Serial.println("Errore avvio PDM!");
    while (1);
  }

  // Inizializzazione Sensore Temperatura
  if (!IMU.begin()) {
    Serial.println("Errore avvio IMU!");
    while(1);
  }

  // Inizializzazione Display LCD
  Wire.begin();
  lcd.begin(16, 2);
  lcd.setBacklight(255);
  lcd.clear();
  lcd.print("System Starting");
  delay(2000);
  lcd.clear();

  // Stampa Menu Seriale
  Serial.println("Controller Avviato. Comandi disponibili:");
  Serial.println("- 'A' : Imposta TAC_min_pres (es. A26.5)");
  Serial.println("- 'B' : Imposta TAC_max_pres (es. B31.0)");
  Serial.println("- 'C' : Imposta THT_min_pres (es. C16.0)");
  Serial.println("- 'D' : Imposta THT_max_pres (es. D21.0)");
}

void loop() {
  unsigned long currentMillis = millis();
  
  // ==========================================
  // LETTURA TEMPERATURA 
  // ==========================================
  float currentTemp = 20.0; // Default
  if (IMU.temperatureAvailable()) {
    int tempInt = 0;
    IMU.readTemperature(tempInt);
    currentTemp = (float)tempInt;
  }

  // ==========================================
  // PUNTO H: LETTURA E AGGIORNAMENTO SERIALE 
  // ==========================================
  if (Serial.available() > 0) {
    char command = Serial.read(); 
    if (command == 'A' || command == 'B' || command == 'C' || command == 'D' ||
        command == 'a' || command == 'b' || command == 'c' || command == 'd') {
        
      float newValue = Serial.parseFloat();
      
      switch(command) {
        case 'A': case 'a':
          TAC_min_pres = newValue;
          Serial.print("Aggiornato TAC_min_pres a: "); Serial.println(TAC_min_pres);
          break;
        case 'B': case 'b':
          TAC_max_pres = newValue;
          Serial.print("Aggiornato TAC_max_pres a: "); Serial.println(TAC_max_pres);
          break;
        case 'C': case 'c':
          THT_min_pres = newValue;
          Serial.print("Aggiornato THT_min_pres a: "); Serial.println(THT_min_pres);
          break;
        case 'D': case 'd':
          THT_max_pres = newValue;
          Serial.print("Aggiornato THT_max_pres a: "); Serial.println(THT_max_pres);
          break;
      }
    } 
  }

  // ==========================================
  // LOGICA DI PRESENZA (PIR E PDM COMBINATI)
  // ==========================================
  if (currentMillis - lastMotionTime > timeout_pir) {
    isPresencePIR = false;
  } else {
    isPresencePIR = true;
  }

  if (samplesRead) {
    bool loudNoise = false;
    for (int i = 0; i < samplesRead; i++) {
      if (abs(sampleBuffer[i]) > sound_threshold) {
        loudNoise = true; break;
      }
    }
    if (loudNoise) {
      if (soundEventsCount == 0) firstEventTime = currentMillis;
      soundEventsCount++;
      lastSoundTime = currentMillis;
    }
    samplesRead = 0; 
  }

  if (soundEventsCount > 0) {
    if (currentMillis - firstEventTime > sound_interval) {
      if (soundEventsCount < n_sound_events) soundEventsCount = 0;
    } else if (soundEventsCount >= n_sound_events) {
      isPresenceSound = true;
      soundEventsCount = 0;
    }
  }

  if (isPresenceSound && (currentMillis - lastSoundTime > timeout_sound)) {
    isPresenceSound = false;
  }

  isRoomOccupied = (isPresencePIR || isPresenceSound);

  // ==========================================
  // AGGIORNAMENTO SET-POINT DINAMICI
  // ==========================================
  if (isRoomOccupied) {
    TAC_min = TAC_min_pres;
    TAC_max = TAC_max_pres;
    THT_max = THT_max_pres;
    THT_min = THT_min_pres;
  } else {
    TAC_min = TAC_min_abs;
    TAC_max = TAC_max_abs;
    THT_max = THT_max_abs;
    THT_min = THT_min_abs;
  }

  // ==========================================
  // ATTUAZIONE (PWM Ventola e Riscaldamento)
  // ==========================================
  int fanSpeed = 0;
  if (currentTemp >= TAC_max) fanSpeed = 255;
  else if (currentTemp > TAC_min) {
    fanSpeed = (int)(((currentTemp - TAC_min) / (TAC_max - TAC_min)) * 255.0);
  }
  analogWrite(FAN_PIN, fanSpeed);
  fanSpeedPercent = map(fanSpeed, 0, 255, 0, 100);

  int heaterIntensity = 0;
  if (currentTemp <= THT_min) heaterIntensity = 255;
  else if (currentTemp < THT_max) {
    heaterIntensity = (int)(((THT_max - currentTemp) / (THT_max - THT_min)) * 255.0);
  }
  analogWrite(RLED_PIN, heaterIntensity);
  heaterIntensityPercent = map(heaterIntensity, 0, 255, 0, 100);

  // ==========================================
  // AGGIORNAMENTO DISPLAY LCD (Punto g)
  // ==========================================
  if (currentMillis - lastDisplaySwitch >= 5000) {
    showScreen1 = !showScreen1;
    lastDisplaySwitch = currentMillis;
    lcd.clear(); 
  }

  lcd.home();
  if (showScreen1) {
    lcd.print("T:");
    lcd.print(currentTemp, 1);
    lcd.print("C Pres:");
    lcd.print(isRoomOccupied ? "1" : "0");

    lcd.setCursor(0, 1); 
    lcd.print("AC:");
    lcd.print(fanSpeedPercent); 
    lcd.print("% HT:");
    lcd.print(heaterIntensityPercent);
    lcd.print("%");
  } else {
    lcd.print("AC m:");
    lcd.print(TAC_min, 1);
    lcd.print(" M:");
    lcd.print(TAC_max, 1);

    lcd.setCursor(0, 1);
    lcd.print("HT m:");
    lcd.print(THT_min, 1);
    lcd.print(" M:");
    lcd.print(THT_max, 1);
  }

  delay(50); // Ritardo per stabilità del loop
}