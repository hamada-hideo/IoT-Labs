#include <PDM.h>

short sampleBuffer[256];
volatile int samplesRead = 0;

void setup() {
  Serial.begin(9600);
  while(!Serial);
  PDM.onReceive(onPDMdata);
  if (!PDM.begin(1, 16000)) {
    Serial.println("Failed to start PDM!");
    while(1);
  }
  Serial.println("Starting");
}

void loop() {
  if (samplesRead) {
    Serial.println("before noInterrupts()");
    noInterrupts();
    Serial.println("after noInterrupts()");
    for (int i = 0; i < samplesRead; i++) {
      Serial.println(sampleBuffer[i]);
    }
    Serial.println("before interrupts()");
    interrupts();
    Serial.println("after interrupts()");
    samplesRead = 0;
  }
}

void onPDMdata() {
  int bytesAvailable = PDM.available();
  PDM.read(sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;
}