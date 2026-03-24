#include <Scheduler.h>
#include <Arduino_LSM6DSOX.h>
#include <Wire.h>
#include <LiquidCrystal_PCF8574.h> // Library needed for LCD display out 

const int GLED_PIN = 2;
const int RLED_PIN = 3;
const int FAN_PIN = 5; // All we need for the fan is to define the pin, as we'll update the speed as necessary directly with
                       // analogWrite


//const int TEMP_PIN = A0; 
//const int B = 4275;        As we're using the onboard sensor, we won't need to use the thermistor to read the temperature       
//const float R0 = 100000.0;       


// Temp detection loop

int lastTemp = 0;
int temperature;
int lowLedTemp = 15; // sets minimum temperature , by which  led bright = 0
int highLedTemp = 20; // sets maximum temperature, by which led bright = 255
int lowFanTemp = 20; // sets minimum temperature, by which fanspeed = 0; 
int highFanTemp = 30; // sets maximum temperature ,by which fanspeed = 255;


LiquidCrystal_PCF8574 lcd(0x27); // Init for display

void setup() 
	{
  	// Serial port communication initialization
  	Serial.begin(9600);
  	while (!Serial); // Waits for serial monitor to open
  	// Prints welcome message 
  	Serial.println("Lab 2.0 starting");
  	if (!IMU.begin()) 
  		{
    	Serial.println("Failed to initialize IMU!");
    	while(1);
  		}
  	// Configurazione dei Pin
  	pinMode(FAN_PIN, OUTPUT);
  	Scheduler.startLoop(loopTemp);

		lcd.begin(16, 2);
		lcd.home();
		lcd.clear();
		lcd.setBacklight(255); // Turns on backlighting 
		lcd.print("Temperature:");
	}

void loop()
	{

		// TEMPERATURE PART
		int propIncrease;
		if(temperature != lastTemp) 										// Avoids evaluating ifs if temp stays the same
		{                                            
			if(temperature >= highFanTemp) // avoids trying to raise fanspeed above 255
			{
				Serial.println("Fan @ max speed");
				analogWrite(FAN_PIN,255); // sets fan to the max (COOLER)
			}
			else if(temperature <= lowFanTemp) // avoids trying to set fanspeed below 0 
			{
				Serial.print("Fan @ min speed");
				analogWrite(FAN_PIN,0); // sets fan to the min	
			}
			else
			{
				propIncrease = (float)(temperature - lowFanTemp) / (highFanTemp - lowFanTemp) * 255; //calculate proportional increase for fanspeed
				analogWrite(FAN_PIN,propIncrease);
			}
			if(temperature >= highLedTemp) // avoids trying to raise fanspeed above 255
			{
				Serial.println("Led @ min brightness");
				analogWrite(RLED_PIN,0); //sets led to the minimum (HEATER)
			}
			else if(temperature <= lowLedTemp) // avoids trying to set fanspeed below 0 
			{
				Serial.print("Led @ max brightness");	
				analogWrite(RLED_PIN,255); // sets led to the max
			}
			else
			{
				propIncrease = (float)(temperature - lowLedTemp) / (highLedTemp - lowLedTemp) * 255; //calculate proportional increase for fanspeed
				analogWrite(RLED_PIN,255 - propIncrease);
			}

		}

      lastTemp = temperature;                                                           
	}

void loopTemp()
   {
   	
   	if (IMU.temperatureAvailable()) 
   		{
    			temperature = 0;
    			lcd.setCursor(12, 0); // edit : setCursor before print
    			IMU.readTemperature(temperature);
    			lcd.print(temperature);
    			// waits 1 sec before proceeding with next read
    			delay(1000);  			
    		}
  			
  }