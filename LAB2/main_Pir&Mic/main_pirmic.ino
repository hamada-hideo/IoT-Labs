#include <Scheduler.h>
#include <Arduino_LSM6DSOX.h>
#include <Wire.h>
#include <PDM.h>


const int PIR_PIN = 4;

short sampleBuffer[256];
volatile int samplesRead = 0;

float highThresh = 2000.0
float lowThresh = 800.0 

int LLT1 = 15; //Low led temp 1 (with presence); SET 1 LED
int HLT1 = 20; // High led temp 1 (with presence); 

int LLT2 = 17; // Low led temp 2 (w/o presnece);  SET 2 LED
int HLT2 = 22; // High led temp 2 (w/o presence); 

int LFT1 = 20; // Low fan temp 1 (w/ presence); SET 1  FAN 
int HFT1 = 30; // High fan temp 1 (w/ presence);

int LFT2 = 22; // Low fan temp 2 (w/o presence); SET 2 FAN  
int HFT2 = 32; // high fan temp 2 (w/o presence);


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
	// SERIAL PART
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
      		if(a > lowThresh && a < highThresh)
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
      				k = 0;
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