// Defining pins through constants 
const int LED_PIN = 2; // Pin for the external LED
const int PIR_PIN = 4; // Pin connected to the digital output of the PIR sensor

// Variable is declared 'volatile' as it will be modified in the ISR
// and subsequently read inside the loop() function
volatile int tot_count = 0;

// Interrupt Service Routine (ISR)
void checkPresence() {
  // 1. Reads the current value of the PIR sensor 
  int pirState = digitalRead(PIR_PIN);

  // 2. Reproduces said value on the LED (ON if HIGH, OFF if LOW) 
  digitalWrite(LED_PIN, pirState);

  // An event is a new movement, because the ISR triggers 
  // both when we go from LOW to HIGH and also when we go from HIGH to LOW  
  // We increase the counter only when the PIR detects a new presence 
  // therefore only when the PIR goes from LOW to HIGH 
  if (pirState == HIGH) {
    tot_count++;
  }
}

void setup() {
  // Configuration of the serial monitor 
  Serial.begin(9600);
  while (!Serial); // Waits for the serial monitor to start 

  // Prints initial msg 
  Serial.println("Lab 1.3 starting");

  // PIN configuration 
  pinMode(LED_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);

  // Associating the ISR to the PIR's PIN 
  // The CHANGE mode makes it so that both the RISING (beginning of the movement) 
  // and FALLING (end of the movement) states are detected 
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), checkPresence, CHANGE);
}

void loop() {
  noInterrupts();
  int a = tot_count;
  interrupts();

  // Sends total count to the serial port 
  Serial.print("Total people count: ");
  Serial.println(a);

  // Waits for 30 seconds (30000 milliseconds) before printing again.
  // Note: using delay() here is correct because the ISR is async 
  delay(30000);
}
