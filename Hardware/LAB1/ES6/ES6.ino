#include <Wire.h>
#include <LiquidCrystal_PCF8574.h> // Library required by the specs 
// Config of temperature resistor 
const int TEMP_PIN = A0; 
const int B = 4275;               
const float R0 = 100000.0;        
// Init of LCD display with I2C address
// Note: standard address sfor PCF8574 modules is 0x27 (otherwise 0x3F) 
LiquidCrystal_PCF8574 lcd(0x27);
void setup() {
  // Init of LCD defining the number of rows and colums (our case : 16x2)
  lcd.begin(16, 2);
  lcd.home();
  lcd.clear();
  lcd.setBacklight(255); // turns on backlighting 
  lcd.print("Temperature:");
}
void loop() {
  // 1. Reads the temperature and proceeds to analog conversion 
  int sensorValue = analogRead(TEMP_PIN);
  float R = 1023.0 / sensorValue - 1.0;
  R = R0 * R;
  float temperature = 1.0 / (log(R / R0) / B + 1 / 298.15) - 273.15; 
  // 2. Updates LCD display 
  lcd.print(temperature);
  lcd.setCursor(12, 0);
  // 3. waits 10 minutes before next temperature reading 
  delay(1000);
}
