#include <Scheduler.h>
#include <Arduino_LSM6DSOX.h>
#include <Wire.h>
#include <LiquidCrystal_PCF8574.h> // Libreria richiesta dalle specifiche

const int GLED_PIN = 2;
const int RLED_PIN = 3;
const int FAN_PIN = 5; 
const int TEMP_PIN = A0; 
const int B = 4275;               
const float R0 = 100000.0;        

	// Variabile per tenere traccia della velocità corrente. 
	// Le slide suggeriscono l'uso di un float
float current_speed = 0;
	// Definizione del numero di step (10 step come richiesto dalle specifiche)
	// Valore massimo PWM è 255. Incremento = 255.0 / 10 = 25.5
const float step_size = 25.5;
int lastTemp = 0;
int temperature;

void setup() 
	{
  	// Configurazione della comunicazione Seriale
  	Serial.begin(9600);
  	while (!Serial); // Attende l'apertura del Serial Monitor
  	// Stampa il messaggio iniziale
  	Serial.println("Lab 2.0 starting");
  	if (!IMU.begin()) 
  		{
    	Serial.println("Failed to initialize IMU!");
    	while(1);
  	  if (!IMU.begin()) {
    	Serial.println("Failed to initialize IMU!");
    	while(1);
  		}
  	// Configurazione dei Pin
  	pinMode(FAN_PIN, OUTPUT);
  	Scheduler.startLoop(loopTemp);

		lcd.begin(16, 2);
		lcd.home();
		lcd.clear();
		lcd.setBacklight(255); // Accende la retroilluminazione
		lcd.print("Temperature:");
	}

void loop()
	{
		if(temperature < lastTemp)
		{
			current_speed -= step_size;
			analogWrite(FAN_PIN, (int)current_speed);

		}
		if(temperature > lastTemp)
		{
			current_speed += step_size;
			analogWrite(FAN_PIN, (int)current_speed);
		}

        lastTemp = temperature;                                                           
	}

void loopTemp()
   {
   	
   	if (IMU.temperatureAvailable()) 
   		{
    			temperature = 0;
    			IMU.readTemperature(temperature);
    			lcd.print(temperature);
    			lcd.setCursor(12, 0);
    			// 3. Attende 10 secondi prima della prossima lettura
    			delay(1000);
  			}
  			
  }