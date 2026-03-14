#include <Wire.h>
#include <LiquidCrystal_PCF8574.h> // Libreria richiesta dalle specifiche
// Configurazione Sensore di Temperatura
const int TEMP_PIN = A0; 
const int B = 4275;               
const float R0 = 100000.0;        
// Inizializzazione del display LCD con indirizzo I2C.
// Nota: l'indirizzo tipico dei moduli PCF8574 è 0x27 (o 0x3F).
LiquidCrystal_PCF8574 lcd(0x27);
void setup() {
  // Inizializza il bus I2C (basato sulla libreria Wire)
  Wire.begin();
  // Inizializza l'LCD definendo il numero di colonne e righe (16x2)
  lcd.begin(16, 2);
  lcd.setBacklight(255); // Accende la retroilluminazione
  // OTTIMIZZAZIONE I2C: 
  // Scriviamo la parte statica del messaggio una sola volta nel setup()
  lcd.setCursor(0, 0);
  lcd.print("Temperature:");
}
void loop() {
  // 1. Lettura e conversione analogica della temperatura
  int sensorValue = analogRead(TEMP_PIN);
  float R = 1023.0 / sensorValue - 1.0;
  R = R0 * R;
  float temperature = 1.0 / (log(R / R0) / B + 1 / 298.15) - 273.15; 
  // 2. Aggiornamento del display LCD
  // Ci posizioniamo sulla seconda riga per aggiornare solo il valore
  lcd.setCursor(0, 1);
  lcd.print(temperature);
  // Aggiungiamo spazi per pulire eventuali caratteri residui 
  // senza dover usare la costosa funzione lcd.clear()
  lcd.print(" C    ");
  // 3. Attende 10 secondi prima della prossima lettura
  delay(10000);
}