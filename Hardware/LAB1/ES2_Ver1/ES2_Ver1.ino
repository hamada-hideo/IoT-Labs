#include <MBED_RPi_Pico_TimerInterrupt.h>
// Defining constants for the LED pins and the periods  
const int RLED_PIN = 2;
const int GLED_PIN = 3;
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
// State variables declared 'volatile' as they are both used inside a loop() and an ISR 
volatile int redLedState = LOW;
volatile int greenLedState = LOW;
// Timer initialized @ 1
MBED_RPI_PICO_Timer ITimer1(1);
// Defined interrupt service routine to make GLED_PIN blink 
void blinkGreen(uint alarm_num) {
  TIMER_ISR_START(alarm_num);
  digitalWrite(GLED_PIN, greenLedState);
  greenLedState = !greenLedState;
  TIMER_ISR_END(alarm_num);
}
// Function used to manage the serial port
void serialPrintStatus() {
  // Checks if there's data avail. on the serial port 
  if (Serial.available() > 0) {
    int inByte = Serial.read(); // Reads received char 
    // Ignores the end of line characters that serial monitor might send 
    if (inByte == '\n' || inByte == '\r') {
        return; 
    }
    if (inByte == 'R') {
      Serial.print("LED ");
      Serial.print(RLED_PIN);
      Serial.print(" Status: ");
      Serial.println(!redLedState);
    } 
    else if (inByte == 'L') {
      Serial.print("LED ");
      Serial.print(GLED_PIN);
      Serial.print(" Status: ");
      Serial.println(!greenLedState);
    } 
    else {
      Serial.println("Invalid command");
    }
  }
}
void setup() {
  // Configures pins as output 
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  // Configures serial port 
  Serial.begin(9600);
  // Waits for the serial connection to start before proceeding 
  while (!Serial); 
  Serial.println("Lab 1.2 Starting");
  // Connects the ISR to a timer which converts time in microseconds
  ITimer1.setInterval(G_HALF_PERIOD * 1000, blinkGreen);
}
void loop() {
  // 1. Controls and manages requests to the serial port 
  serialPrintStatus();
  // 2. Handles the blinking of the red pin
  digitalWrite(RLED_PIN, redLedState);
  redLedState = !redLedState;
  // 3. Pauses the main loop 
  delay(R_HALF_PERIOD); 
}
