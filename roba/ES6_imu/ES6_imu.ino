#include <Wire.h>
#include <LiquidCrystal_PCF8574.h> // Libreria richiesta dalle specifiche
#include <Arduino_LSM6DSOX.h> // Libreria per usare l'IMU
// Configurazione Sensore di Temperatura
const int TEMP_PIN = A0; 
const int B = 4275;               
const float R0 = 100000.0;        
// Inizializzazione del display LCD con indirizzo I2C.
// Nota: l'indirizzo tipico dei moduli PCF8574 è 0x27 (o 0x3F).
LiquidCrystal_PCF8574 lcd(0x27);
void setup() {
  Serial.begin(9600);
  while (!Serial);
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while(1);
  }
  // Inizializza l'LCD definendo il numero di colonne e righe (16x2)
  lcd.begin(16, 2);
  lcd.home();
  lcd.clear();
  lcd.setBacklight(255); // Accende la retroilluminazione
  lcd.print("Temperature:");
}
void loop() {
  if (IMU.temperatureAvailable()) {
    int temperature = 0;
    IMU.readTemperature(temperature);
    lcd.print(temperature);
    lcd.setCursor(12, 0);
    // 3. Attende 10 secondi prima della prossima lettura
    delay(1000);
  }
}