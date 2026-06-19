// Defines the pin that pilots the fan  
// The pin MUST support PWM (Pulse-Width Modulation) 
const int FAN_PIN = 5; 
// this variable keeps track of current fan speed  
float current_speed = 0;
// Defines the number of steps by which the fan speed increases 
// The maximum value allowed by the PWM is equal to 255, therefore 10 steps will be of 25.5 each
const float step_size = 25.5;
void setup() {
  // Init of serial communication 
  Serial.begin(9600);
  while (!Serial); // Waits for the start of the serial monitor  
  // Configures FAN_PIN as output 
  pinMode(FAN_PIN, OUTPUT);
  // Sets initial speed @ 0 (duty cycle = 0%) 
  // Float variable is cast as int 
  analogWrite(FAN_PIN, (int)current_speed);
  Serial.println("Lab 1.4 Starting - Motor Control");
}
void loop() {
  // checks if there's any characters being sent to the serial port 
  if (Serial.available() > 0) {
    char command = Serial.read();
    // Checks for CR and LF characters  
    if (command == '\n' || command == '\r') {
      return;
    }
    // Raises fanspeed whenever a '+' is received  
    if (command == '+') {
      if (current_speed >= 255.0) {
        Serial.println("Already at max speed"); // Upper limit is reached 
      } else {
        current_speed += step_size;
        if (current_speed > 255.0) current_speed = 255.0; // Therefore avoids breaching the limit 
        analogWrite(FAN_PIN, (int)current_speed);
        Serial.print("Increasing speed: ");
        Serial.println(current_speed);
      }
    } 
    // Decreases fanspeed whenever a '-' is received  
    else if (command == '-') {
      if (current_speed <= 0.0) {
        Serial.println("Already at min speed"); // Reaches lower limit  
      } else {
        current_speed -= step_size;
        if (current_speed < 0.0) current_speed = 0.0; // Avoids breaching the limit  
        analogWrite(FAN_PIN, (int)current_speed);
        Serial.print("Decreasing speed: ");
        Serial.println(current_speed);
      }
    } 
   
    // Any other char sent generates an error 
    else {
      Serial.println("Error: Invalid command");
    }
  }
}
