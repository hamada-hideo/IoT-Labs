#include <Scheduler.h>
#include <WiFiNINA.h> //Necessary to rename internal pins 
// Red and green internal pins are renamed  
#define RLED_PIN LEDR
#define GLED_PIN LEDG
// Global constants for the periods are defined 
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
int redLedState = LOW;
int greenLedState = LOW;
void setup() {
  // Serial configuration 
  Serial.begin(9600);
  while (!Serial); // waits for the opening of the serial monitor 
  Serial.println("Lab 1.2 Starting");
  // Configurates PINS as a NINA output  
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  // Starts parallel tasks for the loops  
  Scheduler.startLoop(loopRedLed);
  Scheduler.startLoop(loopGreenLed);
}
// 1. Main loops only listens to the serial port 
void loop() {
  if (Serial.available() > 0) {
    int inByte = Serial.read();   
    // Ignores a newline whenever it is read 
    if (inByte == '\n' || inByte == '\r') {
      yield(); 
      return; 
    }
    if (inByte == 'R') {
      Serial.print("LED RED Status: ");
      Serial.println(!redLedState);
    } 
    else if (inByte == 'L') {
      Serial.print("LED GREEN Status: ");
      Serial.println(!greenLedState);
    } 
    else {
      Serial.println("Invalid command");
    }
  }
  // Explicitly yield control to other loops  
  yield(); 
}
// 2. The second loop only handles the red pin  
void loopRedLed() {

  // Write operations require typecasting to pinstatus for NINA pins 
  digitalWrite(RLED_PIN, (PinStatus) redLedState);
  redLedState = !redLedState; 
  delay(R_HALF_PERIOD); // implictly yields control 
}
// 3. Third loop only handles green pin 
void loopGreenLed() {
  // Once again , typecasting to pinstatus is a necessity with NINA pins  
  digitalWrite(GLED_PIN, (PinStatus) greenLedState);
  greenLedState = !greenLedState; 
  delay(G_HALF_PERIOD); // Yields implictly control 
}
