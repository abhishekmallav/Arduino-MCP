// Master Arduino Control System by Abhishek
// Combines: LCD I2C, TM1637 Display, Ultrasonic Sensor, Buzzer, Built-in LED
// 
// Connections:
// LCD I2C: SCL-10, SDA-11
// TM1637: CLK-8, DIO-9
// Ultrasonic: TRIG-7, ECHO-6
// Buzzer: Pin 13
// Built-in LED: Pin 13 (shared with buzzer)
//
// Command Protocol (JSON-like): CMD:device:action:value
// Examples:
//   LED:ON or LED:OFF
//   LED:BLINK:500 (blink with 500ms interval)
//   BUZZER:ON or BUZZER:OFF
//   BUZZER:BEEP:1000 (beep for 1000ms)
//   LCD:LINE1:Hello World
//   LCD:LINE2:Test
//   LCD:CLEAR
//   TM1637:NUM:1234
//   TM1637:CLEAR
//   ULTRA:START or ULTRA:STOP
//   STATUS (get status of all devices)

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <TM1637Display.h>

// Pin definitions
const int LCD_SCL = 10;
const int LCD_SDA = 11;
const int TM1637_CLK = 8;
const int TM1637_DIO = 9;
const int TRIG_PIN = 7;
const int ECHO_PIN = 6;
const int BUZZER_PIN = 13;
const int LED_PIN = LED_BUILTIN;

// Device objects
LiquidCrystal_I2C lcd(0x27, 16, 2);  // Change to 0x3F if 0x27 doesn't work
TM1637Display tm1637(TM1637_CLK, TM1637_DIO);

// State variables
bool ledState = false;
bool ledBlinking = false;
unsigned long ledBlinkInterval = 500;
unsigned long lastLedBlink = 0;

bool buzzerState = false;
unsigned long buzzerStopTime = 0;

bool ultrasonicActive = false;
unsigned long lastUltrasonicRead = 0;
const unsigned long ultrasonicInterval = 200;

// LCD Clock state
bool lcdClockActive = false;
int lcdClockHours = 0;
int lcdClockMinutes = 0;
int lcdClockSeconds = 0;
String lcdClockDate = "";
String lcdClockDay = "";
unsigned long lastLcdClockUpdate = 0;
const unsigned long lcdClockInterval = 1000; // Update every second

// LCD Stopwatch state
bool lcdStopwatchActive = false;
unsigned long lcdStopwatchStartTime = 0;
unsigned long lastLcdStopwatchUpdate = 0;

// TM1637 Clock state
bool tm1637ClockActive = false;
int tm1637ClockHours = 0;
int tm1637ClockMinutes = 0;
unsigned long lastTm1637ClockUpdate = 0;
const unsigned long tm1637ClockInterval = 1000; // Update every second

// TM1637 Stopwatch state
bool tm1637StopwatchActive = false;
unsigned long tm1637StopwatchStartTime = 0;
unsigned long lastTm1637StopwatchUpdate = 0;

// TM1637 Countdown state
bool tm1637CountdownActive = false;
int countdownSeconds = 0;
unsigned long countdownStartTime = 0;
unsigned long lastCountdownUpdate = 0;
const unsigned long countdownInterval = 1000; // Update every second

// Status reporting
unsigned long lastStatusReport = 0;
const unsigned long statusReportInterval = 500; // Send status every 500ms

void setup() {
  Serial.begin(9600);
  
  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("System Ready");
  
  // Initialize TM1637
  tm1637.setBrightness(0x0f);
  tm1637.clear();
  
  // Initialize Ultrasonic
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  // Initialize Buzzer and LED
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
  
  delay(1000);
  lcd.clear();
}

void loop() {
  // Handle serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processCommand(command);
  }
  
  // Handle LED blinking
  if (ledBlinking) {
    unsigned long currentMillis = millis();
    if (currentMillis - lastLedBlink >= ledBlinkInterval) {
      lastLedBlink = currentMillis;
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState ? HIGH : LOW);
    }
  }
  
  // Handle buzzer timeout
  if (buzzerState && buzzerStopTime > 0 && millis() >= buzzerStopTime) {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerState = false;
    buzzerStopTime = 0;
  }
  
  // Handle ultrasonic readings
  if (ultrasonicActive && (millis() - lastUltrasonicRead >= ultrasonicInterval)) {
    lastUltrasonicRead = millis();
    float distance = getUltrasonicDistance();
    Serial.print("ULTRA:");
    Serial.print(distance);
    Serial.println();
  }
  
  // Handle LCD Clock (ACTUAL TIME from PC)
  if (lcdClockActive && (millis() - lastLcdClockUpdate >= lcdClockInterval)) {
    lastLcdClockUpdate = millis();
    
    // Increment seconds (PC sends actual time, we just tick)
    lcdClockSeconds++;
    if (lcdClockSeconds >= 60) {
      lcdClockSeconds = 0;
      lcdClockMinutes++;
      if (lcdClockMinutes >= 60) {
        lcdClockMinutes = 0;
        lcdClockHours++;
        if (lcdClockHours >= 24) {
          lcdClockHours = 0;
        }
      }
    }
    
    // Display: Line 1 = Time, Line 2 = Date + Day
    lcd.setCursor(0, 0);
    lcd.print("                "); // Clear line
    lcd.setCursor(0, 0);
    if (lcdClockHours < 10) lcd.print("0");
    lcd.print(lcdClockHours);
    lcd.print(":");
    if (lcdClockMinutes < 10) lcd.print("0");
    lcd.print(lcdClockMinutes);
    lcd.print(":");
    if (lcdClockSeconds < 10) lcd.print("0");
    lcd.print(lcdClockSeconds);
    
    lcd.setCursor(0, 1);
    lcd.print("                "); // Clear line
    lcd.setCursor(0, 1);
    lcd.print(lcdClockDate); // Date sent from PC
    lcd.print(" ");
    lcd.print(lcdClockDay); // Day sent from PC
  }
  
  // Handle LCD Stopwatch (COUNT UP from 00:00:00)
  if (lcdStopwatchActive && (millis() - lastLcdStopwatchUpdate >= 1000)) {
    lastLcdStopwatchUpdate = millis();
    unsigned long elapsedSeconds = (millis() - lcdStopwatchStartTime) / 1000;
    
    int hours = elapsedSeconds / 3600;
    int minutes = (elapsedSeconds / 60) % 60;
    int seconds = elapsedSeconds % 60;
    
    lcd.setCursor(0, 0);
    lcd.print("Stopwatch:      ");
    lcd.setCursor(0, 1);
    if (hours < 10) lcd.print("0");
    lcd.print(hours);
    lcd.print(":");
    if (minutes < 10) lcd.print("0");
    lcd.print(minutes);
    lcd.print(":");
    if (seconds < 10) lcd.print("0");
    lcd.print(seconds);
    lcd.print("        ");
  }
  
  // Handle TM1637 Clock (ACTUAL TIME - HH:MM only)
  if (tm1637ClockActive && (millis() - lastTm1637ClockUpdate >= tm1637ClockInterval)) {
    lastTm1637ClockUpdate = millis();
    
    // Increment seconds internally, update display every minute
    static int tm1637Seconds = 0;
    tm1637Seconds++;
    if (tm1637Seconds >= 60) {
      tm1637Seconds = 0;
      tm1637ClockMinutes++;
      if (tm1637ClockMinutes >= 60) {
        tm1637ClockMinutes = 0;
        tm1637ClockHours++;
        if (tm1637ClockHours >= 24) {
          tm1637ClockHours = 0;
        }
      }
    }
    
    // Display HH:MM format
    char timeStr[5];
    sprintf(timeStr, "%02d%02d", tm1637ClockHours, tm1637ClockMinutes);
    
    uint8_t data[4];
    data[0] = tm1637.encodeDigit(timeStr[0] - '0');
    data[1] = tm1637.encodeDigit(timeStr[1] - '0') | 0x80; // Add colon
    data[2] = tm1637.encodeDigit(timeStr[2] - '0');
    data[3] = tm1637.encodeDigit(timeStr[3] - '0');
    tm1637.setSegments(data);
  }
  
  // Handle TM1637 Stopwatch (COUNT UP - HH:MM format)
  if (tm1637StopwatchActive && (millis() - lastTm1637StopwatchUpdate >= 1000)) {
    lastTm1637StopwatchUpdate = millis();
    unsigned long elapsedSeconds = (millis() - tm1637StopwatchStartTime) / 1000;
    
    int hours = (elapsedSeconds / 3600) % 24;
    int minutes = (elapsedSeconds / 60) % 60;
    
    char timeStr[5];
    sprintf(timeStr, "%02d%02d", hours, minutes);
    
    uint8_t data[4];
    data[0] = tm1637.encodeDigit(timeStr[0] - '0');
    data[1] = tm1637.encodeDigit(timeStr[1] - '0') | 0x80;
    data[2] = tm1637.encodeDigit(timeStr[2] - '0');
    data[3] = tm1637.encodeDigit(timeStr[3] - '0');
    tm1637.setSegments(data);
  }
  
  // Handle TM1637 Countdown
  if (tm1637CountdownActive && (millis() - lastCountdownUpdate >= countdownInterval)) {
    lastCountdownUpdate = millis();
    unsigned long elapsedSeconds = (millis() - countdownStartTime) / 1000;
    int remainingSeconds = countdownSeconds - elapsedSeconds;
    
    if (remainingSeconds <= 0) {
      // Countdown finished!
      tm1637CountdownActive = false;
      remainingSeconds = 0;
      
      // Show 00:00 and beep
      uint8_t data[4] = {0, 0x80, 0, 0}; // 00:00
      tm1637.setSegments(data);
      
      // Quick beeps
      for (int i = 0; i < 3; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(100);
        digitalWrite(BUZZER_PIN, LOW);
        delay(100);
      }
      
      Serial.println("COUNTDOWN:FINISHED");
    } else {
      // Display MM:SS format
      int mins = remainingSeconds / 60;
      int secs = remainingSeconds % 60;
      
      char timeStr[5];
      sprintf(timeStr, "%02d%02d", mins, secs);
      
      uint8_t data[4];
      data[0] = tm1637.encodeDigit(timeStr[0] - '0');
      data[1] = tm1637.encodeDigit(timeStr[1] - '0') | 0x80; // Add colon
      data[2] = tm1637.encodeDigit(timeStr[2] - '0');
      data[3] = tm1637.encodeDigit(timeStr[3] - '0');
      tm1637.setSegments(data);
      
      // Send remaining time to Python
      Serial.print("TIMER:REMAINING:");
      Serial.println(remainingSeconds);
    }
  }
  
  // Periodic status reporting
  if (millis() - lastStatusReport >= statusReportInterval) {
    lastStatusReport = millis();
    sendAutoStatus();
  }
}

void sendAutoStatus() {
  // Send current timer status if countdown is active
  if (tm1637CountdownActive) {
    unsigned long elapsedSeconds = (millis() - countdownStartTime) / 1000;
    int remainingSeconds = countdownSeconds - elapsedSeconds;
    if (remainingSeconds > 0) {
      Serial.print("TIMER:REMAINING:");
      Serial.println(remainingSeconds);
    }
  }
  
  // Send current time if clock is active
  if (lcdClockActive) {
    Serial.print("CLOCK:LCD:");
    if (lcdClockHours < 10) Serial.print("0");
    Serial.print(lcdClockHours);
    Serial.print(":");
    if (lcdClockMinutes < 10) Serial.print("0");
    Serial.print(lcdClockMinutes);
    Serial.print(":");
    if (lcdClockSeconds < 10) Serial.print("0");
    Serial.println(lcdClockSeconds);
  }
  
  // Send ultrasonic distance if active
  if (ultrasonicActive) {
    float distance = getUltrasonicDistance();
    Serial.print("DISTANCE:");
    Serial.println(distance);
  }
}

void processCommand(String cmd) {
  // Parse command format: DEVICE:ACTION:VALUE
  int firstColon = cmd.indexOf(':');
  if (firstColon == -1) {
    Serial.println("ERROR:Invalid command format");
    return;
  }
  
  String device = cmd.substring(0, firstColon);
  String rest = cmd.substring(firstColon + 1);
  
  int secondColon = rest.indexOf(':');
  String action = secondColon == -1 ? rest : rest.substring(0, secondColon);
  String value = secondColon == -1 ? "" : rest.substring(secondColon + 1);
  
  device.toUpperCase();
  action.toUpperCase();
  
  // Route to appropriate handler
  if (device == "LED") {
    handleLED(action, value);
  } else if (device == "BUZZER") {
    handleBuzzer(action, value);
  } else if (device == "LCD") {
    handleLCD(action, value);
  } else if (device == "TM1637" || device == "DISPLAY") {
    handleTM1637(action, value);
  } else if (device == "ULTRA") {
    handleUltrasonic(action);
  } else if (device == "STATUS") {
    sendStatus();
  } else {
    Serial.println("ERROR:Unknown device");
  }
}

void handleLED(String action, String value) {
  if (action == "ON") {
    ledBlinking = false;
    digitalWrite(LED_PIN, HIGH);
    ledState = true;
    Serial.println("OK:LED:ON");
  } else if (action == "OFF") {
    ledBlinking = false;
    digitalWrite(LED_PIN, LOW);
    ledState = false;
    Serial.println("OK:LED:OFF");
  } else if (action == "BLINK") {
    ledBlinking = true;
    ledBlinkInterval = value.length() > 0 ? value.toInt() : 500;
    lastLedBlink = millis();
    Serial.print("OK:LED:BLINK:");
    Serial.println(ledBlinkInterval);
  } else if (action == "TOGGLE") {
    if (!ledBlinking) {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState ? HIGH : LOW);
      Serial.print("OK:LED:TOGGLE:");
      Serial.println(ledState ? "ON" : "OFF");
    }
  }
}

void handleBuzzer(String action, String value) {
  if (action == "ON") {
    digitalWrite(BUZZER_PIN, HIGH);
    buzzerState = true;
    buzzerStopTime = 0;
    Serial.println("OK:BUZZER:ON");
  } else if (action == "OFF") {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerState = false;
    buzzerStopTime = 0;
    Serial.println("OK:BUZZER:OFF");
  } else if (action == "BEEP") {
    int duration = value.length() > 0 ? value.toInt() : 100;
    digitalWrite(BUZZER_PIN, HIGH);
    buzzerState = true;
    buzzerStopTime = millis() + duration;
    Serial.print("OK:BUZZER:BEEP:");
    Serial.println(duration);
  }
}

void handleLCD(String action, String value) {
  if (action == "LINE1") {
    lcdClockActive = false; // Stop clock if active
    lcdStopwatchActive = false; // Stop stopwatch if active
    lcd.setCursor(0, 0);
    lcd.print("                "); // Clear line
    lcd.setCursor(0, 0);
    lcd.print(value.substring(0, 16));
    Serial.println("OK:LCD:LINE1");
  } else if (action == "LINE2") {
    lcdClockActive = false; // Stop clock if active
    lcdStopwatchActive = false; // Stop stopwatch if active
    lcd.setCursor(0, 1);
    lcd.print("                "); // Clear line
    lcd.setCursor(0, 1);
    lcd.print(value.substring(0, 16));
    Serial.println("OK:LCD:LINE2");
  } else if (action == "CLEAR") {
    lcdClockActive = false; // Stop clock if active
    lcdStopwatchActive = false; // Stop stopwatch if active
    lcd.clear();
    Serial.println("OK:LCD:CLEAR");
  } else if (action == "BACKLIGHT") {
    if (value == "ON") {
      lcd.backlight();
      Serial.println("OK:LCD:BACKLIGHT:ON");
    } else if (value == "OFF") {
      lcd.noBacklight();
      Serial.println("OK:LCD:BACKLIGHT:OFF");
    }
  } else if (action == "CLOCK") {
    // Format: CLOCK:HH:MM:SS:Date:Day
    // Example: CLOCK:14:30:45:07/12/2025:Sat
    lcdStopwatchActive = false; // Stop stopwatch if active
    lcdClockActive = true;
    
    // Parse time components
    int firstColon = value.indexOf(':');
    int secondColon = value.indexOf(':', firstColon + 1);
    int thirdColon = value.indexOf(':', secondColon + 1);
    int fourthColon = value.indexOf(':', thirdColon + 1);
    
    lcdClockHours = value.substring(0, firstColon).toInt();
    lcdClockMinutes = value.substring(firstColon + 1, secondColon).toInt();
    lcdClockSeconds = value.substring(secondColon + 1, thirdColon).toInt();
    lcdClockDate = value.substring(thirdColon + 1, fourthColon);
    lcdClockDay = value.substring(fourthColon + 1);
    
    lastLcdClockUpdate = millis();
    lcd.clear();
    Serial.println("OK:LCD:CLOCK:START");
  } else if (action == "STOPWATCH") {
    if (value == "START") {
      lcdClockActive = false; // Stop clock if active
      lcdStopwatchActive = true;
      lcdStopwatchStartTime = millis();
      lastLcdStopwatchUpdate = 0;
      lcd.clear();
      Serial.println("OK:LCD:STOPWATCH:START");
    } else if (value == "STOP") {
      lcdStopwatchActive = false;
      lcd.clear();
      Serial.println("OK:LCD:STOPWATCH:STOP");
    }
  }
}

void handleTM1637(String action, String value) {
  if (action == "NUM") {
    tm1637ClockActive = false; // Stop clock if active
    tm1637CountdownActive = false; // Stop countdown if active
    
    int number = value.toInt();
    if (value.length() == 4) {
      // Display with colon for time format
      uint8_t data[4];
      data[0] = tm1637.encodeDigit(value.charAt(0) - '0');
      data[1] = tm1637.encodeDigit(value.charAt(1) - '0') | 0x80; // Add colon
      data[2] = tm1637.encodeDigit(value.charAt(2) - '0');
      data[3] = tm1637.encodeDigit(value.charAt(3) - '0');
      tm1637.setSegments(data);
    } else {
      tm1637.showNumberDec(number, true);
    }
    Serial.println("OK:TM1637:NUM");
  } else if (action == "CLEAR") {
    tm1637ClockActive = false; // Stop clock if active
    tm1637CountdownActive = false; // Stop countdown if active
    tm1637.clear();
    Serial.println("OK:TM1637:CLEAR");
  } else if (action == "BRIGHTNESS") {
    int brightness = value.toInt();
    brightness = constrain(brightness, 0, 15);
    tm1637.setBrightness(brightness);
    Serial.print("OK:TM1637:BRIGHTNESS:");
    Serial.println(brightness);
  } else if (action == "CLOCK") {
    // Format: CLOCK:HH:MM
    // Example: CLOCK:14:30
    tm1637CountdownActive = false; // Stop countdown if active
    tm1637StopwatchActive = false; // Stop stopwatch if active
    tm1637ClockActive = true;
    
    int colonPos = value.indexOf(':');
    tm1637ClockHours = value.substring(0, colonPos).toInt();
    tm1637ClockMinutes = value.substring(colonPos + 1).toInt();
    tm1637ClockSeconds = 0;
    
    lastTm1637ClockUpdate = millis();
    Serial.println("OK:TM1637:CLOCK:START");
  } else if (action == "STOPWATCH") {
    if (value == "START") {
      tm1637CountdownActive = false; // Stop countdown if active
      tm1637ClockActive = false; // Stop clock if active
      tm1637StopwatchActive = true;
      tm1637StopwatchStartTime = millis();
      lastTm1637StopwatchUpdate = 0;
      Serial.println("OK:TM1637:STOPWATCH:START");
    } else if (value == "STOP") {
      tm1637StopwatchActive = false;
      tm1637.clear();
      Serial.println("OK:TM1637:STOPWATCH:STOP");
    }
  } else if (action == "COUNTDOWN") {
    // Format: COUNTDOWN:seconds
    tm1637ClockActive = false; // Stop clock if active
    tm1637CountdownActive = true;
    countdownSeconds = value.toInt();
    countdownStartTime = millis();
    lastCountdownUpdate = 0;
    
    // Show initial countdown value
    int mins = countdownSeconds / 60;
    int secs = countdownSeconds % 60;
    char timeStr[5];
    sprintf(timeStr, "%02d%02d", mins, secs);
    uint8_t data[4];
    data[0] = tm1637.encodeDigit(timeStr[0] - '0');
    data[1] = tm1637.encodeDigit(timeStr[1] - '0') | 0x80;
    data[2] = tm1637.encodeDigit(timeStr[2] - '0');
    data[3] = tm1637.encodeDigit(timeStr[3] - '0');
    tm1637.setSegments(data);
    
    Serial.print("OK:TM1637:COUNTDOWN:");
    Serial.println(countdownSeconds);
  }
}

void handleUltrasonic(String action) {
  if (action == "START") {
    ultrasonicActive = true;
    lastUltrasonicRead = 0;
    Serial.println("OK:ULTRA:START");
  } else if (action == "STOP") {
    ultrasonicActive = false;
    Serial.println("OK:ULTRA:STOP");
  } else if (action == "READ") {
    float distance = getUltrasonicDistance();
    Serial.print("ULTRA:");
    Serial.println(distance);
  }
}

float getUltrasonicDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  if (duration == 0) {
    return -1; // No echo received
  }
  
  float distanceCm = duration * 0.0343 / 2;
  return distanceCm;
}

void sendStatus() {
  Serial.println("STATUS:START");
  Serial.print("LED:");
  Serial.println(ledState ? (ledBlinking ? "BLINKING" : "ON") : "OFF");
  Serial.print("BUZZER:");
  Serial.println(buzzerState ? "ON" : "OFF");
  Serial.print("ULTRASONIC:");
  Serial.println(ultrasonicActive ? "ACTIVE" : "INACTIVE");
  Serial.println("STATUS:END");
}
