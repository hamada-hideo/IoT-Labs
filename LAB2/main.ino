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



// Display
LiquidCrystal_PCF8574 lcd(0x27);


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
	lcd.print("Temperature:");

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
		if(presence)
		{	
			lowLedTemp = LLT1;
			highLedTemp = HLT1;
			lowFanTemp = LFT1; 
			highFanTemp = HFT1;
		}
		if(!presence)
		{

			lowLedTemp = LLT2;
			highLedTemp = HLT2;
			lowFanTemp = LFT2; 
			highFanTemp = HFT2;

		}

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
    	static unsigned long lastReadTime = 0; // remembers last read time; static means it persists between calls

    	if(millis() - lastReadTime >= 1000) // has 1 second passed since last read?
    	{
        	lastReadTime = millis(); // update the timestamp immediately

        	if (IMU.temperatureAvailable())
        	{
            	IMU.readTemperature(temperature);
            	lcd.setCursor(12, 0);
            	lcd.print(temperature);
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