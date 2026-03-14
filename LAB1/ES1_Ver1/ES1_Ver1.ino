//Write a sketch that drives two LEDs, so they blink with independent periods.
// The sketch must meet the following specifications:
#include <MBED_RPi_Pico_TimerInterrupt.h>
//The pins to which the two LEDs are connected,
// and the blinking (semi-)periods, must be defined using constants.
//As a test, use blinking periods that are not multiples of each other (e.g. 3s and 7s) 
// and connect the two LEDs to pins D2 and D3 on the board.
const int RLED_PIN = 2;
const int GLED_PIN = 3;
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
int redLedState = LOW;
int greenLedState = LOW;
MBED_RPI_PICO_Timer ITimer1(1);
//To drive the second LED, use an Interrupt Service Routine connected to the MCU Timer1 
// (using the MBED_RPI_PICO_TimerInterrupt library or the Scheduler library).
void blinkGreen(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  digitalWrite(GLED_PIN, greenLedState);
  greenLedState = !greenLedState;
  TIMER_ISR_END(alarm_num);
}
void setup() {
  // put your setup code here, to run once:
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  ITimer1.setInterval(G_HALF_PERIOD * 1000, blinkGreen);
}
//To drive the first LED, use the delay() function within the loop()
void loop() {
  // put your main code here, to run repeatedly:
  digitalWrite(RLED_PIN, redLedState);
  redLedState = !redLedState;
  delay(R_HALF_PERIOD);
}
