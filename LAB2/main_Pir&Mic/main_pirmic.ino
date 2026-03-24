#include <Scheduler.h>
#include <Arduino_LSM6DSOX.h>
#include <Wire.h>
#include <PDM.h>


const int PIR_PIN = 4;

short sampleBuffer[256];
volatile int samplesRead = 0;

LLT1 = 15; //Low led temp 1 (with presence);
HLT1 = 20; // High led temp 1 (with presence);
LLT2 = 17; // Low led temp 2 (w/o presnece);
HLT2 = 22; // High led temp 2 (w/o presence);

LFT1 = 20; // Low fan temp 1 (w/ presence);
HFT1 = 30; // High fan temp 1 (w/ presence);
LFT2 = 22; // Low fan temp 2 (w/o presence);
HFT2 = 32; // high fan temp 2 (w/o presence);


void setup() 
	{
  	// Serial port communication initialization
  	Serial.begin(9600);
  	while (!Serial); // Waits for serial monitor to open
  	// Prints welcome message 
  	Serial.println("Lab 2.0 starting");
  	
  	
	lcd.begin(16, 2);
	lcd.home();
	lcd.clear();
	lcd.setBacklight(255); // Turns on backlighting 

	 pinMode(PIR_PIN, INPUT);
	 Scheduler.startLoop(loopPIR);
	 Scheduler.startLoop(loopMic);

	}

void loop()
	{
		noInterrupts();
		bool presence = pirPresence || micPresence; 
		interrupts();

		if(presence)
		{
		// TEMPERATURE PART with set 1
		}
		if(!presence)
		{
		//TEMPERATURE PART with set 2
		}

      lastTemp = temperature;
                                                                 
	}


void loopMic()
{

	int begTime;
	int micState; 
	if (samplesRead) 
	{
		begTime = millis();
    	for (int i = 0; i < samplesRead; i++) 
    	{
      		noInterrupts();
      		int a = sampleBuffer[i];
      		interrupts();
      		if(a)
      		{
      			if(k == 0)
      			{
      				begTime = millis();
      			}
      			k++;
      			lastTime = millis();
      			if(k == 10 && (lastTime - begTime) < 60000)
      			{
      				micState = 1;
      				noInterrupts();
      				micPresence = 1;
      				interrupts();
      			}
      		}

      		
      		Serial.println(a);
    }
    samplesRead = 0;
  }


}

void onPDMdata() 
	{
  		int bytesAvailable = PDM.available();
  		PDM.read(sampleBuffer, bytesAvailable);
  		samplesRead = bytesAvailable / 2;
	}

void loopPIR()
{
	int pirState = digitalRead(PIR_PIN);
	noInterrupts();
	if(pirState)
	{	
		
		pirPresence = 1;
		
	}
	interrupts();
	delay(1800000);
}