#include <Scheduler.h>
// Constants for LED pins and periods 
const int RLED_PIN = 2;
const int GLED_PIN = 3;
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;

// LED states are not volatile because they wont be used in an ISR 
int redLedState = LOW;
int greenLedState = LOW;
void setup() {
  // Serial port configuration 
  Serial.begin(9600);
  while (!Serial); // waits for serial monitor to start  
  Serial.println("Lab 1.2 Starting (Scheduler Version)");
  // Pin configuration  
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  // Starts the parallel loops  
  Scheduler.startLoop(loopRedLed);
  Scheduler.startLoop(loopGreenLed);
}
// 1. The main loop just listens to the serial port  
void loop() {
  if (Serial.available() > 0) {
    int inByte = Serial.read();
    if (inByte == '\n' || inByte == '\r') {
      yield(); // Cedes control whenever an end of line char is read 
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
 

  // Very important: yield() explicitly cedes control to other loops 
  // whenever there aren't blocking operations (such as delay()) 
  yield(); 
}
// 2. Second loop only handles the red led 
void loopRedLed() {
  digitalWrite(RLED_PIN, redLedState);
  redLedState = !redLedState;
  // delay implicitly cedes control to scheduler  
  delay(R_HALF_PERIOD); 
}
// 3. Third loop only handles green led  
void loopGreenLed() {
  digitalWrite(GLED_PIN, greenLedState);
  greenLedState = !greenLedState;
  // Once again delay implicitly cedes control to the scheduler 
  delay(G_HALF_PERIOD); 
}
