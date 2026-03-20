#include <Scheduler.h>
const int GLED_PIN = 2;
const int RLED_PIN = 3;
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
int redLedState = LOW;
int greenLedState = LOW;
void setup() {
  // put your setup code here, to run once:
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  Scheduler.startLoop(loop2);
}
//To drive the first LED, use the delay() function within the loop()
void loop() {
  // put your main code here, to run repeatedly:
  digitalWrite(RLED_PIN, redLedState);
  redLedState = !redLedState;
  delay(R_HALF_PERIOD);
}

//To drive the second LED, use an Interrupt Service Routine connected to 
//the MCU Timer1 (using the MBED_RPI_PICO_TimerInterrupt library or the Scheduler library).
void loop2(){
  digitalWrite(GLED_PIN, greenLedState);
  greenLedState = !greenLedState;
  delay(G_HALF_PERIOD);
}

