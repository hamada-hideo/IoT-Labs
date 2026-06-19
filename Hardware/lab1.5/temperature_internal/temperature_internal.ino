#include <Arduino_LSM6DSOX.h>

unsigned long lastReadTime = 0;
const unsigned long READ_INTERVAL = 10000; // 10 seconds

void setup() {
  Serial.begin(9600);
  while (!Serial); // Waits for the Serial Monitor to open
  
  Serial.println("Lab 1.5 starting");

  // Initialization of the internal sensor (IMU)
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }
}

void loop() {
  // Non-blocking periodic reading
  if (millis() - lastReadTime >= READ_INTERVAL) {
    lastReadTime = millis();

    if (IMU.temperatureAvailable()) {
      int current_temp = 0; // Changed from float to int to match the library signature
      IMU.readTemperature(current_temp); // Reads the temperature in °C
      
      Serial.print("temperature = ");
      Serial.println(current_temp);
    }
  }
}
