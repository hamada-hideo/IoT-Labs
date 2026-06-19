#include <Scheduler.h>     // Necessary Library to simulate multi-threading 
#include <WiFiNINA.h>      // Necessary to communicate with built-in LED
// Redefines the internal led pins for green and red 
#define RLED_PIN LEDR
#define GLED_PIN LEDG
// Global constats for the semi-periods
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
int redLedState = LOW;
int greenLedState = LOW;
void setup() {
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  // Starts a second loop to avoid usage of ISRs 
  Scheduler.startLoop(loop2);
}
void loop() {

  // Write operations must use type-casting to PinStatus  for NINA pins
  digitalWrite(RLED_PIN, (PinStatus) redLedState);
  redLedState = !redLedState;
  delay(R_HALF_PERIOD); // Releases control at the end of the loop 
}
void loop2() {
  // Same as before, the type-casting is necessary
  digitalWrite(GLED_PIN, (PinStatus) greenLedState);
  greenLedState = !greenLedState;
  delay(G_HALF_PERIOD); // Releases control to make it so that the other loop can take control
}
