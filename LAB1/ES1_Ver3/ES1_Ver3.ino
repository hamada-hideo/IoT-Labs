#include <Scheduler.h>     // Libreria per simulare il multi-tasking
#include <WiFiNINA.h>      // Necessaria per comunicare con il LED RGB interno
// Uso di define per ridenominare i pin interni del LED RGB
#define RLED_PIN LEDR
#define GLED_PIN LEDG
// Costanti globali per i semi-periodi
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
int redLedState = LOW;
int greenLedState = LOW;
void setup() {
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  // Avvia il secondo loop usando lo Scheduler (evita le ISR)
  Scheduler.startLoop(loop2);
}
void loop() {
  // Scrittura con type-casting a PinStatus obbligatorio per i pin NINA
  digitalWrite(RLED_PIN, (PinStatus) redLedState);
  redLedState = !redLedState;
  delay(R_HALF_PERIOD); // Rilascia il controllo al termine dell'operazione
}
void loop2() {
  // Scrittura con type-casting a PinStatus obbligatorio
  digitalWrite(GLED_PIN, (PinStatus) greenLedState);
  greenLedState = !greenLedState;
  delay(G_HALF_PERIOD); // Rilascia il controllo per far eseguire l'altro loop
}