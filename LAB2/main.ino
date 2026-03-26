#include <Scheduler.h>
#include <PDM.h>
#include <Arduino_LSM6DSOX.h>
#include <Wire.h>
#include <LiquidCrystal_PCF8574.h> // Library needed for LCD display out 

const int GLED_PIN = 2;
const int RLED_PIN = 3;
const int FAN_PIN = 5; // All we need for the fan is to define the pin, as we'll update the speed as necessary directly with
                       // analogWrite


// TEMP LOOP VARIABLES

int lastTemp = 0;
int temperature;
int lowLedTemp; // sets minimum temperature , by which  led bright = 0
int highLedTemp; // sets maximum temperature, by which led bright = 255
int lowFanTemp; // sets minimum temperature, by which fanspeed = 0; 
int highFanTemp; // sets maximum temperature ,by which fanspeed = 255;



int LLT1 = 15; //Low led temp 1 (with presence); SET 1 LED
int HLT1 = 20; // High led temp 1 (with presence); 

int LLT2 = 17; // Low led temp 2 (w/o presnece);  SET 2 LED
int HLT2 = 22; // High led temp 2 (w/o presence); 

int LFT1 = 20; // Low fan temp 1 (w/ presence); SET 1  FAN 
int HFT1 = 30; // High fan temp 1 (w/ presence);

int LFT2 = 22; // Low fan temp 2 (w/o presence); SET 2 FAN  
int HFT2 = 32; // high fan temp 2 (w/o presence);


// MOTION LOOP VARIABLES


const int PIR_PIN = 4;

const unsigned long timeout_pir = 1800000; // 30 mins in ms
const unsigned long timeout_sound = 60000; // 1 min in ms 
short sampleBuffer[256];
volatile int samplesRead = 0;

float highThresh = 2000.0;
float lowThresh = 800.0;
volatile bool pirPresence, micPresence;
bool manual = 0;


// Display
LiquidCrystal_PCF8574 lcd(0x27);
int fanPercent = 0;
int heaterPercent = 0;
int currentScreen = 0;

void setup() 
	{

  	// Serial port communication initialization
  	Serial.begin(9600);
  	while (!Serial); // Waits for serial monitor to open
  	// Prints welcome message 
  	Serial.println("Lab 2.0 starting");

  	if (!IMU.begin()) // IMU temp sensor init 
  		{
    	Serial.println("Failed to initialize IMU!");
    	while(1);
  		}
  	// MIC conf
  	PDM.onReceive(onPDMdata);
	PDM.begin(1, 16000); // mono, 16kHz

  	// Pin configuration
  	pinMode(FAN_PIN, OUTPUT);
  	pinMode(PIR_PIN, INPUT);
  	

  	// LCD init

	lcd.begin(16, 2);
	lcd.home();
	lcd.clear();
	lcd.setBacklight(255); // Turns on backlighting 
	

	// Loop init	
	Scheduler.startLoop(loopPIR);
	Scheduler.startLoop(loopMic);
	Scheduler.startLoop(loopTemp);

	}


void loop()
	{

		//MOTION PART

		noInterrupts();
		bool presence = pirPresence || micPresence; 
		interrupts();
		if(presence && !manual)
		{	
			lowLedTemp = LLT1;
			highLedTemp = HLT1;
			lowFanTemp = LFT1; 
			highFanTemp = HFT1;
		}
		else if(!presence && !manual)
		{

			lowLedTemp = LLT2;
			highLedTemp = HLT2;
			lowFanTemp = LFT2; 
			highFanTemp = HFT2;

		}
		else
		{

			if (Serial.available())
			{
	    	String command = Serial.readStringUntil('\n');
	    	command.trim(); // removes trailing whitespace/newline characters

	    	// expects format: "SET LLT1 18"
	    	if (command.startsWith("SET "))
	    	{
	        	String body = command.substring(4); // removes "SET ", leaves "LLT1 18"
	        	int spaceIndex = body.indexOf(' '); // finds the space between variable and value
	        
	        	if (spaceIndex != -1)
	        {
	            String varName = body.substring(0, spaceIndex); // "LLT1"
	            int value = body.substring(spaceIndex + 1).toInt(); // "18" -> 18

	            if      (varName == "LLT1") LLT1 = value;
	            else if (varName == "HLT1") HLT1 = value;
	            else if (varName == "LLT2") LLT2 = value;
	            else if (varName == "HLT2") HLT2 = value;
	            else if (varName == "LFT1") LFT1 = value;
	            else if (varName == "HFT1") HFT1 = value;
	            else if (varName == "LFT2") LFT2 = value;
	            else if (varName == "HFT2") HFT2 = value;
	            else Serial.println("Unknown variable");

	            Serial.print("Updated "); 
	            Serial.print(varName); 
	            Serial.print(" to "); 
	            Serial.println(value);
	        	}
	    	}
			}
		}

		// TEMPERATURE PART

		int propIncrease;
		if(temperature != lastTemp) 										// Avoids evaluating ifs if temp stays the same
		{   `                                         
			if(temperature >= highFanTemp) // avoids trying to raise fanspeed above 255
			{
				Serial.println("Fan @ max speed");
				analogWrite(FAN_PIN,255); // sets fan to the max (COOLER)
				fanPercent = 100;
			}
			else if(temperature <= lowFanTemp) // avoids trying to set fanspeed below 0 
			{
				Serial.print("Fan @ min speed");
				analogWrite(FAN_PIN,0); // sets fan to the min	
				fanPercent = 0;
			}
			else
			{
				propIncrease = (float)(temperature - lowFanTemp) / (highFanTemp - lowFanTemp) * 255; //calculate proportional increase for fanspeed
				analogWrite(FAN_PIN,propIncrease);
				fanPercent = (float)propIncrease/255 * 100;
			}
			if(temperature >= highLedTemp) // avoids trying to raise fanspeed above 255
			{
				Serial.println("Led @ min brightness");
				analogWrite(RLED_PIN,0); //sets led to the minimum (HEATER)
				heaterPercent = 0;
			}
			else if(temperature <= lowLedTemp) // avoids trying to set fanspeed below 0 
			{
				Serial.print("Led @ max brightness");	
				analogWrite(RLED_PIN,255); // sets led to the max
				heaterPercent = 100; 
			}
			else
			{
				propIncrease = (float)(temperature - lowLedTemp) / (highLedTemp - lowLedTemp) * 255; //calculate proportional increase for fanspeed
				analogWrite(RLED_PIN,255 - propIncrease);
				heaterPercent = 100 - (float)propIncrease/255 * 100;
			}

		}
	  lastTemp = temperature; 
	  // DISPLAY PART 
	  static unsigned long lastScreenSwitch = 0;
	  if(millis() - lastScreenSwitch >= 5000)
	  {
	  	lastScreenSwitch = millis();
	  	currentScreen = (currentScreen + 1) % 4; // cycles 0->1->2->3->0
	  	lcd.clear();
	  
	  switch(currentScreen)
	  {
	  	case 0:
	  	lcd.setCursor(0, 0);
	  	lcd.print("Temperature:");
	  	lcd.setCursor(0,1);
	  	lcd.print(temperature);
	  	break;
	  	case 1: 
	  	lcd.setCursor(0,0);
	  	lcd.print("Fan %:");
	  	lcd.print(fanPercent);
	  	lcd.setCursor(0,1);
	  	lcd.print("Heater %:");
	  	lcd.print(heaterPercent);
	  	break;
	  	case 2:
	  	lcd.setCursor(0,0);
	  	if(presence)
	  	{
	  		lcd.print("Presence: Y");
	  	}
	  	if(!presence)
	  	{
	  		lcd.print("Presence: N");
	  	}
	  	break;
	  	case 3:
	  	//First Row
	  	lcd.setCursor(0,0);
	  	lcd.print(" LEDS    FAN");
	  	//Second Row
	  	lcd.setCursor(0,1);
	  	lcd.print(lowLedTemp);
	  	lcd.setCursor(3,1); // Sets 1 space inbetween
	  	lcd.print(highLedTemp);
	  	lcd.setCursor(9,1); //sets 4 spaces inbetween leds and fan temps 
	  	lcd.print(lowFanTemp);
	  	lcd.setCursor(12,1); // sets 1 space inbetween
	  	lcd.print(highFanTemp);
	  	break; 
	  }

  }
}







void loopTemp() 
	{
    	static unsigned long lastReadTime = 0; // remembers last read time; static means it persists between calls

    	if(millis() - lastReadTime >= 1000) // has 1 second passed since last read?
    	{
        	lastReadTime = millis(); // update the timestamp immediately

        	if (IMU.temperatureAvailable())
        	{
            	IMU.readTemperature(temperature);
          
        	}
    	}
    	yield(); // hands control back to the scheduler so other loops can run
	}


void loopPIR() 
	{
    	static unsigned long lastMotionTime = 0; // remembers when motion was last detected

    	int pirState = digitalRead(PIR_PIN);

    	if (pirState) // motion detected right now
    	{
        	lastMotionTime = millis(); // reset the clock
        	noInterrupts();
        	pirPresence = true;
        	interrupts();
    	}

    	// if no motion has been detected for timeout_pir milliseconds, clear presence
    	if (pirPresence && (millis() - lastMotionTime >= timeout_pir))
    	{
        	noInterrupts();
        	pirPresence = false;
        	interrupts();
    	}

    	yield(); // without this the loop hogs the scheduler
	}

void loopMic()
	{
		static int k; 
		static unsigned long begTime;
		static unsigned long lastTime; 
		if (samplesRead) 
		{
    		for (int i = 0; i < samplesRead; i++) 
    		{
      			noInterrupts();
      			int a = sampleBuffer[i];
      			interrupts();
      			if(a > lowThresh && a < highThresh)
      			{
      				if(k == 0)
      				{
      					begTime = millis();
      				}
      				k++;
      				lastTime = millis();
      				if(k % 10 == 0 && (lastTime - begTime) < 60000)
      				{
      					noInterrupts();
      					micPresence = 1;
      					interrupts();
      					k = 0;
      				}
      				
      			}

				if(micPresence && (millis() - lastTime >= timeout_sound))
      				{
      					noInterrupts();
      					micPresence = 0;
      					interrupts();
      				} 
      			Serial.println(a);
    		}
    	noInterrupts();
    	samplesRead = 0;
    	interrupts();

    	
  		}

  		yield();
	}

void onPDMdata()
{
  int bytesAvailable = PDM.available();
  PDM.read(sampleBuffer, bytesAvailable);
  noInterrupts();
  samplesRead = bytesAvailable / 2;
  interrupts();
}