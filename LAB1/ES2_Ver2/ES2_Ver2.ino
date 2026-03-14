#include <Scheduler.h>
// Costanti per i pin dei LED e i semi-periodi
const int RLED_PIN = 2;
const int GLED_PIN = 3;
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
// Lo stato dei LED (senza la necessità della keyword volatile)
int redLedState = LOW;
int greenLedState = LOW;
void setup() {
  // Configurazione Seriale
  Serial.begin(9600);
  while (!Serial); // Attende l'apertura del Serial Monitor
  Serial.println("Lab 1.2 Starting (Scheduler Version)");
  // Configurazione Pin
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  // Avvia i task paralleli
  Scheduler.startLoop(loopRedLed);
  Scheduler.startLoop(loopGreenLed);
}
// 1. Loop Principale: dedicato interamente all'ascolto Seriale
void loop() {
  if (Serial.available() > 0) {
    int inByte = Serial.read();
    if (inByte == '\n' || inByte == '\r') {
      yield(); // Cede il controllo se legge un fine riga
      return; 
    }
    if (inByte == 'R') {
      Serial.print("LED ");
      Serial.print(RLED_PIN);
      Serial.print(" Status: ");
      Serial.println(redLedState);
    } 
    else if (inByte == 'L') {
      Serial.print("LED ");
      Serial.print(GLED_PIN);
      Serial.print(" Status: ");
      Serial.println(greenLedState);
    } 
    else {
      Serial.println("Invalid command");
    }
  }
  // Fondamentale: yield() cede esplicitamente il controllo agli altri loop
  // quando non ci sono operazioni bloccanti (come un delay)
  yield(); 
}
// 2. Secondo Loop: gestisce solo il LED rosso
void loopRedLed() {
  digitalWrite(RLED_PIN, redLedState);
  redLedState = !redLedState;
  // delay() cede implicitamente il controllo allo Scheduler
  delay(R_HALF_PERIOD); 
}
// 3. Terzo Loop: gestisce solo il LED verde
void loopGreenLed() {
  digitalWrite(GLED_PIN, greenLedState);
  greenLedState = !greenLedState;
  // delay() cede implicitamente il controllo allo Scheduler
  delay(G_HALF_PERIOD); 
}