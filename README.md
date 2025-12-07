<div align="center">

# 🤖 Arduino Master Control (Arduino-MCP)

### AI-Powered Hardware Automation Platform

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Arduino](https://img.shields.io/badge/Arduino-Compatible-00979D.svg)](https://www.arduino.cc/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Enabled-green.svg)](https://github.com/jlowin/fastmcp)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*Bridge the gap between AI agents and physical hardware with intelligent, event-driven automation*

[Features](#-key-features) • [Hardware](#-hardware-stack) • [Quick Start](#-quick-start) • [Examples](#-example-workflows) • [Expand](#-extensibility--future-enhancements)

</div>

---

## 📋 Table of Contents

- [What is Arduino-MCP?](#-what-is-arduino-mcp)
- [Key Features](#-key-features)
- [What Makes This Project Unique](#-what-makes-this-project-unique)
- [Hardware Stack](#-hardware-stack)
- [System Architecture](#-system-architecture)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Quick Start](#-quick-start)
- [Example Workflows](#-example-workflows)
- [API Reference](#-api-reference)
- [Extensibility & Future Enhancements](#-extensibility--future-enhancements)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 What is Arduino-MCP?

**Arduino-MCP** is an AI-controlled automation platform that bridges Python AI agents with Arduino-based hardware peripherals. It enables complex, multi-step scenarios without manual supervision by combining:

- **Live Hardware Control**: Real-time updates to displays, sensors, and actuators
- **Event-Driven Automation**: Background monitoring and conditional trigger execution
- **AI Integration**: High-level tools designed for natural language AI agent control
- **Non-Blocking Architecture**: Firmware runs multiple concurrent tasks seamlessly

### The Problem It Solves

Traditional Arduino projects require:
- Manual, continuous control or blocking code
- Complex state management for multi-device coordination
- Constant polling for time-based or sensor-triggered events
- Difficult integration with AI/automation systems

### The Solution

Arduino-MCP provides:
- ✅ **High-level Python API** for intuitive control
- ✅ **Automatic background monitoring** of timers, clocks, and sensors
- ✅ **Conditional execution engine** that chains actions without polling
- ✅ **Live displays** that update on-device without Python intervention
- ✅ **FastMCP integration** for seamless AI agent communication

---

## ✨ Key Features

### 🖥️ Display Management

| Display Type | Capabilities | Key Functions |
|-------------|-------------|---------------|
| **LCD (16×2)** | Live clock, stopwatch, custom text, backlight control | `lcd_show_current_time()`, `lcd_start_stopwatch()`, `lcd_write_line1/2()` |
| **TM1637 7-Segment** | Live clock, countdown timer, stopwatch, numbers | `display_current_time()`, `display_timer()`, `display_number()` |

### 🔧 Hardware Control

| Component | Actions | Functions |
|-----------|---------|-----------|
| **LED** | On/Off, Blink, Toggle | `led_on()`, `led_off()`, `led_blink(interval_ms)`, `led_toggle()` |
| **Buzzer** | On/Off, Timed beep | `buzzer_on()`, `buzzer_off()`, `buzzer_beep(duration_ms)` |
| **Ultrasonic Sensor** | Single read, continuous monitoring, live LCD stream | `ultrasonic_read()`, `ultrasonic_start()`, `show_live_ultrasonic_on_lcd()` |

### ⚡ Conditional Automation (The Star Feature!)

**Background-triggered actions** that execute automatically without polling:

| Trigger Type | When It Fires | Example Use Case |
|-------------|---------------|------------------|
| `when_timer_finishes()` | Countdown reaches 00:00 | Auto-beep when timer done, chain timers |
| `when_time_equals()` | Clock matches specific time | Start tasks at scheduled times |
| `when_distance_less_than()` | Object gets too close | Proximity alerts, collision prevention |

**Available Actions:**
- `buzzer_beep` — Sound alert
- `start_timer` — Begin countdown
- `led_blink` — Visual indicator
- `display_message` — Show text on LCD

---

## 🌟 What Makes This Project Unique

### 1. **True Live Behaviors**
Unlike typical Arduino sketches that require constant Python calls, our firmware runs displays and timers **autonomously** in non-blocking loops:
- Clocks tick every second automatically
- Countdowns decrement without Python intervention
- Same strategy as LED blinking — set it once, it runs forever

### 2. **AI-First Design**
Built specifically for AI agent control via FastMCP:
- High-level, intent-driven functions
- Natural language compatible tool descriptions
- Complex scenario parsing built-in (e.g., "start timer, then beep, then start another timer at 7:15 AM")

### 3. **Conditional Execution Engine**
Python background monitor watches Arduino status messages and **automatically executes queued actions**:
```python
display_timer(1, 30)  # Start 90-second countdown
when_timer_finishes("buzzer_beep", "1000")  # Auto-beep when done
when_timer_finishes("start_timer", "02:00")  # Auto-start 2-min timer after first ends
# No polling loop needed - monitor handles everything!
```

### 4. **Multi-Device Orchestration**
Unified control of LCD, 7-segment display, LED, buzzer, and ultrasonic sensor with synchronized state management.

### 5. **Zero Manual Polling**
Traditional approach: `while True: check_status(); sleep(1)`  
Arduino-MCP approach: Set trigger → Background monitor → Action executes automatically

---

## 🔌 Hardware Stack

### Components

| Component | Model/Type | Connection | Notes |
|-----------|-----------|------------|-------|
| **LCD Display** | 16×2 I2C (`LiquidCrystal_I2C`) | SCL→10, SDA→11 | Default address: `0x27` (try `0x3F` if needed) |
| **7-Segment Display** | 4-digit TM1637 | CLK→8, DIO→9 | Brightness adjustable (0-15) |
| **Ultrasonic Sensor** | HC-SR04 or similar | TRIG→7, ECHO→6 | Range: 2-400cm |
| **Buzzer** | Active buzzer | Pin 13 | Shares pin with LED |
| **LED** | Built-in | `LED_BUILTIN` | Usually pin 13 |

### Wiring Diagram

```
Arduino Uno/Nano
├── LCD I2C ────────► SCL: Pin 10, SDA: Pin 11
├── TM1637 ─────────► CLK: Pin 8, DIO: Pin 9
├── Ultrasonic ─────► TRIG: Pin 7, ECHO: Pin 6
├── Buzzer ─────────► Pin 13
└── LED (built-in) ─► Pin 13 (LED_BUILTIN)
```

### Required Libraries

Install via Arduino Library Manager:
- `LiquidCrystal_I2C` by Frank de Brabander
- `TM1637Display` by Avishay Orpaz

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Python Layer (FastMCP)                   │
├─────────────────────────────────────────────────────────────┤
│  arduino_mcp_server.py                                       │
│  ├── High-level Tools (led_on, display_timer, etc.)        │
│  ├── Background Monitor Thread                              │
│  │   ├── Reads: TIMER:REMAINING, COUNTDOWN:FINISHED        │
│  │   ├── Reads: CLOCK:LCD:HH:MM:SS, DISTANCE:<cm>         │
│  │   └── Executes: Queued conditional actions              │
│  └── Conditional Engine (when_timer_finishes, etc.)        │
└─────────────────────────────────────────────────────────────┘
                            ↕ Serial (9600 baud)
┌─────────────────────────────────────────────────────────────┐
│                    Arduino Layer (Firmware)                  │
├─────────────────────────────────────────────────────────────┤
│  master_control.ino                                          │
│  ├── Non-blocking loop() orchestrates all devices           │
│  ├── Command Protocol: DEVICE:ACTION:VALUE                  │
│  │   Example: LED:BLINK:500, TM1637:COUNTDOWN:90           │
│  ├── Display Modes:                                         │
│  │   ├── LCD: clock, stopwatch, static text               │
│  │   └── TM1637: clock, countdown, stopwatch, numbers      │
│  └── Status Broadcasting (auto-reports state)              │
└─────────────────────────────────────────────────────────────┘
                            ↕
                    ┌───────────────┐
                    │   Hardware    │
                    │   Peripherals │
                    └───────────────┘
```

### Communication Protocol

| Command | Format | Example | Description |
|---------|--------|---------|-------------|
| LED Control | `LED:ACTION[:VALUE]` | `LED:BLINK:500` | Blink LED every 500ms |
| Buzzer | `BUZZER:ACTION[:VALUE]` | `BUZZER:BEEP:1000` | Beep for 1 second |
| LCD | `LCD:ACTION:VALUE` | `LCD:LINE1:Hello World` | Write to LCD line 1 |
| TM1637 | `TM1637:ACTION:VALUE` | `TM1637:COUNTDOWN:90` | Start 90-second countdown |
| Ultrasonic | `ULTRA:ACTION` | `ULTRA:START` | Begin continuous monitoring |
| Status | `STATUS` | `STATUS` | Get all device states |

---

## 📦 Prerequisites

### Hardware
- Arduino Uno, Nano, or compatible board
- USB cable for programming and serial communication
- Components listed in [Hardware Stack](#-hardware-stack)

### Software

| Requirement | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10+ | MCP server and scripts |
| **Arduino IDE** | 1.8+ or 2.x | Firmware upload |
| **pyserial** | Latest | Serial communication |
| **fastmcp** | Latest | AI agent integration |

### Operating System
- **Windows** (default COM port: `COM6`)
- macOS/Linux compatible with COM port adjustment

---

## 🚀 Installation & Setup

### Step 1: Arduino Firmware

1. **Open Arduino IDE**
   ```
   File → Open → master_control.ino
   ```

2. **Install Required Libraries**
   ```
   Sketch → Include Library → Manage Libraries
   Search: "LiquidCrystal_I2C" → Install
   Search: "TM1637Display" → Install
   ```

3. **Verify Wiring**
   - Double-check connections match [Hardware Stack](#-hardware-stack)
   - Test LCD I2C address (try `0x27`, fallback `0x3F`)

4. **Upload to Board**
   ```
   Tools → Board → Arduino Uno (or your model)
   Tools → Port → COM6 (or your port)
   Upload ✓
   ```

### Step 2: Python Environment

1. **Install Dependencies**
   ```powershell
   pip install pyserial fastmcp
   ```

2. **Configure COM Port**
   - Edit `arduino_mcp_server.py` and `master_control.py`
   - Set `COM_PORT = "COM6"` (adjust to your port)
   - Check Device Manager (Windows) or `ls /dev/tty*` (Linux/Mac)

3. **Verify Connection**
   ```python
   from arduino_mcp_server import test_connection
   print(test_connection())
   # Expected: ✓ SUCCESS: Arduino is connected and ready on COM6
   ```

---

## ⚡ Quick Start

### Option 1: FastMCP Server (For AI Agents)

```powershell
python arduino_mcp_server.py
```

The server exposes tools that AI agents can call directly.

### Option 2: Interactive CLI (For Manual Testing)

```powershell
python master_control.py
```

Try these commands:
```
led blink 500
buzzer beep 200
lcd 1:Hello Arduino!
display clock
ultra start
```

### Your First Automation

```python
from arduino_mcp_server import (
    display_timer, 
    when_timer_finishes, 
    lcd_show_current_time
)

# Start a 30-second countdown on 7-segment display
display_timer(0, 30)

# When countdown finishes, beep 3 times (1 second each)
when_timer_finishes("buzzer_beep", "1000")

# Show live clock on LCD while timer runs
lcd_show_current_time()
```

---

## 💡 Example Workflows

### 1. Kitchen Timer with Alert

```python
from arduino_mcp_server import display_timer, when_timer_finishes, lcd_display_message

# 5-minute cooking timer
display_timer(5, 0)

# Show message on LCD
lcd_display_message("Cooking Timer", "5:00 remaining")

# Beep 5 times when done
when_timer_finishes("buzzer_beep", "500")
```

### 2. Scheduled Task Automation

```python
from arduino_mcp_server import lcd_show_current_time, when_time_equals, led_blink

# Display live clock
lcd_show_current_time()

# At 7:15 AM, start blinking LED (morning alarm)
when_time_equals("07:15:00", "led_blink", "1000")

# At 7:16 AM, show message
when_time_equals("07:16:00", "display_message", "Wake Up!|Time to Start")
```

### 3. Proximity Security System

```python
from arduino_mcp_server import (
    ultrasonic_start, 
    when_distance_less_than, 
    show_live_ultrasonic_on_lcd
)

# Start monitoring distance and show on LCD
show_live_ultrasonic_on_lcd()

# If object closer than 15cm, trigger alarm
when_distance_less_than(15, "buzzer_beep", "2000")
when_distance_less_than(15, "led_blink", "100")
```

### 4. Multi-Stage Countdown Chain

```python
from arduino_mcp_server import display_timer, when_timer_finishes

# Workout timer: 45 sec work → beep → 15 sec rest → beep → repeat
display_timer(0, 45)
when_timer_finishes("buzzer_beep", "500")
when_timer_finishes("start_timer", "00:15")
# Add more stages as needed!
```

### 5. Status Dashboard

```python
from arduino_mcp_server import (
    get_current_status,
    lcd_show_current_time,
    display_current_time,
    ultrasonic_start
)

# Show time on both displays
lcd_show_current_time()
display_current_time()

# Monitor distance
ultrasonic_start()

# Check system status
print(get_current_status())
```

---

## 📚 API Reference

### Display Functions

| Function | Parameters | Description |
|----------|-----------|-------------|
| `lcd_show_current_time()` | — | Live PC time on LCD (updates every second) |
| `lcd_start_stopwatch()` | — | Count up from 00:00:00 on LCD |
| `lcd_write_line1(text)` | `text: str` | Static text on LCD line 1 (max 16 chars) |
| `lcd_write_line2(text)` | `text: str` | Static text on LCD line 2 |
| `lcd_display_message(line1, line2)` | `line1, line2: str` | Write both lines at once |
| `lcd_clear()` | — | Clear entire LCD |
| `display_current_time()` | — | Live PC time on 7-segment (HH:MM) |
| `display_timer(minutes, seconds)` | `minutes, seconds: int` | **Live countdown** to 00:00 with auto-beep |
| `display_start_stopwatch()` | — | Count up from 00:00 on 7-segment |
| `display_number(number)` | `number: int` | Show static number (-999 to 9999) |
| `display_clear()` | — | Clear 7-segment display |

### Actuator Functions

| Function | Parameters | Description |
|----------|-----------|-------------|
| `led_on()` | — | Turn LED on (solid) |
| `led_off()` | — | Turn LED off |
| `led_blink(interval_ms)` | `interval_ms: int` (default: 500) | Blink continuously |
| `led_toggle()` | — | Flip LED state once |
| `buzzer_on()` | — | Continuous buzzer (call `buzzer_off()` to stop) |
| `buzzer_off()` | — | Silence buzzer |
| `buzzer_beep(duration_ms)` | `duration_ms: int` (default: 100) | Single beep, auto-stops |

### Sensor Functions

| Function | Parameters | Description |
|----------|-----------|-------------|
| `ultrasonic_read()` | — | Single distance measurement (cm) |
| `ultrasonic_start()` | — | Continuous monitoring (200ms intervals) |
| `ultrasonic_stop()` | — | Stop monitoring |
| `show_live_ultrasonic_on_lcd()` | — | Display + auto-update distance on LCD |

### Conditional Automation

| Function | Parameters | Description |
|----------|-----------|-------------|
| `when_timer_finishes(action, params)` | `action: str`, `params: str` | Execute action when countdown → 0 |
| `when_time_equals(time, action, params)` | `time: "HH:MM:SS"`, `action: str`, `params: str` | Execute at specific clock time |
| `when_distance_less_than(cm, action, params)` | `cm: float`, `action: str`, `params: str` | Execute when object too close |

**Available Actions:**
- `"buzzer_beep"` — params: duration in ms (e.g., `"1000"`)
- `"start_timer"` — params: `"MM:SS"` format (e.g., `"02:30"`)
- `"led_blink"` — params: interval in ms (e.g., `"500"`)
- `"display_message"` — params: `"Line1|Line2"` (e.g., `"Alert!|Object Near"`)

### System Functions

| Function | Description |
|----------|-------------|
| `get_current_status()` | Get timer, clock, distance, pending actions |
| `clear_all_pending_actions()` | Cancel all queued triggers |
| `all_off()` | Turn off/clear all devices (emergency stop) |
| `test_connection()` | Verify Arduino connection |

---

## 🔧 Extensibility & Future Enhancements

### Easy to Expand

Arduino-MCP is designed for extensibility. Here's how you can enhance it:

#### 1. **Add New Hardware**

**Example: Adding a Servo Motor**

*Arduino Firmware (`master_control.ino`):*
```cpp
#include <Servo.h>
Servo myservo;

void setup() {
  myservo.attach(5);  // Servo on pin 5
}

void handleServo(String action, String value) {
  if (action == "MOVE") {
    int angle = value.toInt();
    myservo.write(angle);
    Serial.println("OK:SERVO:MOVE");
  }
}

// Add to processCommand():
else if (device == "SERVO") {
  handleServo(action, value);
}
```

*Python Server (`arduino_mcp_server.py`):*
```python
@mcp.tool()
def servo_move(angle: int) -> str:
    """Move servo to specified angle (0-180 degrees)"""
    if angle < 0 or angle > 180:
        return "Error: Angle must be 0-180"
    response = send_command(f"SERVO:MOVE:{angle}")
    return f"Servo moved to {angle}°"
```

#### 2. **Add New Sensors**

| Sensor Type | Integration Complexity | Potential Use Cases |
|------------|------------------------|---------------------|
| **Temperature/Humidity (DHT22)** | Easy | Climate monitoring, auto-fan control |
| **Light Sensor (LDR)** | Easy | Auto-brightness, day/night detection |
| **PIR Motion Sensor** | Easy | Security alerts, auto-lighting |
| **Gas/Smoke Detector** | Medium | Safety alarms, air quality |
| **GPS Module** | Medium | Location tracking, geofencing |

#### 3. **Extend Conditional Actions**

Add more trigger types in `arduino_mcp_server.py`:
```python
@mcp.tool()
def when_temperature_above(threshold: float, then_action: str, params: str) -> str:
    """Execute action when temperature exceeds threshold"""
    action = {
        "trigger": "temp_above",
        "target_temp": threshold,
        "action_type": then_action,
        "params": parse_params(params)
    }
    pending_actions.append(action)
    return f"✅ Will execute '{then_action}' when temp > {threshold}°C"
```

#### 4. **Create Complex Scenarios**

**Multi-Device Morning Routine:**
```python
def morning_routine():
    # 6:30 AM: Start gentle alarm
    when_time_equals("06:30:00", "led_blink", "2000")
    
    # 6:45 AM: Louder alarm
    when_time_equals("06:45:00", "buzzer_beep", "500")
    
    # 7:00 AM: Show schedule on LCD
    when_time_equals("07:00:00", "display_message", "Good Morning!|Check Schedule")
```

### Future Enhancement Ideas

| Enhancement | Difficulty | Impact |
|-------------|-----------|--------|
| **Web Dashboard** | Medium | Real-time monitoring via browser |
| **MQTT Integration** | Medium | IoT device network compatibility |
| **Voice Control** | Medium-High | "Alexa, start the timer" |
| **Data Logging** | Low | Historical sensor data storage |
| **Mobile App** | High | Remote control via smartphone |
| **Multi-Board Support** | Medium | Control multiple Arduinos |
| **Machine Learning** | High | Predictive automation based on patterns |
| **Relay Control** | Easy | Control high-voltage appliances |
| **RGB LED Strips** | Easy-Medium | Advanced lighting effects |
| **SD Card Logging** | Medium | Offline data persistence |

---

## 📁 Project Structure

```
Arduino-MCP/
│
├── arduino_mcp_server.py      # FastMCP server with tools + conditional engine
│   ├── Tool definitions (@mcp.tool decorators)
│   ├── Background monitor thread
│   ├── Conditional execution engine
│   └── Serial communication layer
│
├── master_control.ino          # Arduino firmware
│   ├── Non-blocking loop() architecture
│   ├── Device handlers (LED, buzzer, LCD, TM1637, ultrasonic)
│   ├── Command parser
│   └── Status broadcasting
│
├── master_control.py           # Async CLI controller for manual testing
│   ├── Interactive command menu
│   ├── Human-friendly interface
│   └── Testing utilities
│
├── README.md                   # This file
├── LICENSE                     # MIT License
└── .gitignore                  # Git ignore rules
```

---

## 🐛 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **LCD shows nothing** | • Try I2C address `0x3F` instead of `0x27` in firmware<br>• Check wiring (SCL→10, SDA→11)<br>• Verify backlight is on: `lcd_backlight_on()` |
| **Port not found error** | • Check Device Manager (Windows) or `ls /dev/tty*` (Linux)<br>• Update `COM_PORT` in Python files<br>• Ensure no other program is using the port |
| **Clock shows wrong time** | • Clock initializes from PC time, then ticks<br>• Re-call `lcd_show_current_time()` to re-sync |
| **Countdown doesn't beep** | • Ensure buzzer is connected to pin 13<br>• Active buzzer required (not passive)<br>• Check `buzzer_beep()` function works independently |
| **Ultrasonic gives -1** | • Check wiring (TRIG→7, ECHO→6)<br>• Ensure object is 2-400cm away<br>• Sensor needs clear line of sight |
| **Commands not responding** | • Arduino may have reset (wait 2 seconds after connect)<br>• Check baud rate is 9600 in firmware and Python<br>• Call `test_connection()` to verify |

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check Arduino status:
```python
from arduino_mcp_server import get_current_status
print(get_current_status())
```

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Areas for Contribution
- 🔧 New hardware integrations (sensors, actuators)
- 📚 Documentation improvements
- 🐛 Bug fixes and testing
- 💡 Feature suggestions and implementations
- 🌍 Multi-language support
- 🎨 Web dashboard development

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Test thoroughly with actual hardware
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastMCP** by Marvin Halbach for the excellent MCP framework
- **Arduino Community** for hardware libraries and inspiration
- **AI Agent Developers** who inspire intelligent hardware control

---

<div align="center">

### 🌟 Star this repo if you find it useful!

**Built with ❤️ for makers, tinkerers, and AI enthusiasts**

[Report Bug](https://github.com/abhishekmallav/Arduino-MCP/issues) • [Request Feature](https://github.com/abhishekmallav/Arduino-MCP/issues) • [Discussions](https://github.com/abhishekmallav/Arduino-MCP/discussions)

</div>
