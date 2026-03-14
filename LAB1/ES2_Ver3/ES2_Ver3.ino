#include <Scheduler.h>
#include <WiFiNINA.h> // Necessaria per i LED RGB interni
// Uso di define per ridenominare i pin interni del LED RGB
#define RLED_PIN LEDR
#define GLED_PIN LEDG
// Costanti globali per i semi-periodi
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
int redLedState = LOW;
int greenLedState = LOW;
void setup() {
  // Configurazione Seriale
  Serial.begin(9600);
  while (!Serial); // Attende l'apertura del Serial Monitor
  Serial.println("Lab 1.2 Starting");
  // Configurazione dei pin NINA come output
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  // Avvia i task paralleli per i LED
  Scheduler.startLoop(loopRedLed);
  Scheduler.startLoop(loopGreenLed);
}
// 1. Loop Principale: dedicato all'ascolto Seriale
void loop() {
  if (Serial.available() > 0) {
    int inByte = Serial.read();   
    // Ignora i ritorni a capo
    if (inByte == '\n' || inByte == '\r') {
      yield(); 
      return; 
    }
    if (inByte == 'R') {
      Serial.print("LED RED Status: ");
      Serial.println(redLedState);
    } 
    else if (inByte == 'L') {
      Serial.print("LED GREEN Status: ");
      Serial.println(greenLedState);
    } 
    else {
      Serial.println("Invalid command");
    }
  }
  // Rilascia esplicitamente il controllo agli altri loop
  yield(); 
}
// 2. Loop dedicato al LED Rosso
void loopRedLed() {
  // Scrittura con type-casting a PinStatus obbligatorio per i pin NINA
  digitalWrite(RLED_PIN, (PinStatus) redLedState);
  redLedState = !redLedState; 
  delay(R_HALF_PERIOD); // Rilascia il controllo implicitamente
}
// 3. Loop dedicato al LED Verde
void loopGreenLed() {
  // Scrittura con type-casting a PinStatus obbligatorio
  digitalWrite(GLED_PIN, (PinStatus) greenLedState);
  greenLedState = !greenLedState; 
  delay(G_HALF_PERIOD); // Rilascia il controllo implicitamente
}