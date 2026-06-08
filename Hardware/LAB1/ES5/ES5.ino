
// 1. Defines analog pin for the sensor, specifically it is reccomended to use the pin A0

const int TEMP_PIN = A0; 
// Typical constants for a thermistor in a Grove Temperature Sensor
// Note: Using the formula found in the datasheet  
// The B and R0 values defined below are the standard value for this specific module 
const int B = 4275;               // Value B of thermistor 
const float R0 = 100000.0;        // R0 = 100k ohm
void setup() {
  // Init of serial comms 
  Serial.begin(9600);
  while (!Serial); // waits for opening of serial monitor 
  // prints beginning msg 
  Serial.println("Lab 1.5 starting");
}
void loop() {
  // Reads voltage value of the pin (between 0 and 1023)
  int sensorValue = analogRead(TEMP_PIN);
  // 2. Converts the analog value to a temperature 
  // The grove sensor utilizes a variable resistance (thermistor) 
  float R = 1023.0 / sensorValue - 1.0;
  R = R0 * R;
  // Uses the equation of the thermistor to determine Celsius degrees 
  float temperature = 1.0 / (log(R / R0) / B + 1 / 298.15) - 273.15; 
  // 3. Sends the temperature measurement to PC 
  // formats the output 
  Serial.print("temperature = ");
  Serial.println(temperature);
  // 4. Waits 10 minutes before next measurement 
  delay(10000);
}
