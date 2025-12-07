## Repo Structure

```
arduino_mcp_server.py   # FastMCP tools + conditional engine
master_control.ino      # Arduino firmware for displays/sensors/actuators
master_control.py       # Async CLI controller for manual testing
README.md               # Project overview (this file)
LICENSE                 # License
```

## Notes & Tips

- If the LCD shows nothing, try I2C address `0x3F` in firmware.
- If time appears offset, re-send the clock command to re-sync.
- `display_timer` runs live on Arduino; Python does not need to poll.
- Use `all_off()` to clear displays, silence buzzer, stop ultrasonic.

## License

See `LICENSE` for details.
## Example Workflows

1) Live clock on displays:

```python
from arduino_mcp_server import lcd_show_current_time, display_current_time

lcd_show_current_time()
display_current_time()
```

2) Countdown then chained actions:

```python
from arduino_mcp_server import display_timer, when_timer_finishes

print(display_timer(1, 30))
print(when_timer_finishes("buzzer_beep", "1000"))
print(when_timer_finishes("start_timer", "02:00"))
```

3) Time-based trigger (requires LCD clock running):

```python
from arduino_mcp_server import lcd_show_current_time, when_time_equals

lcd_show_current_time()
print(when_time_equals("07:15:00", "start_timer", "02:00"))
```

4) Proximity automation:

```python
from arduino_mcp_server import ultrasonic_start, when_distance_less_than

ultrasonic_start()
print(when_distance_less_than(10, "buzzer_beep", "500"))
```
## Quick Start

Run the FastMCP server (exposes tools to AI/clients):

```powershell
python d:\VS-Code\Arduino-MCP\arduino_mcp_server.py
```

Optional: Use the async CLI controller for manual testing:

```powershell
python d:\VS-Code\Arduino-MCP\master_control.py
```
## Architecture

- `arduino_mcp_server.py` (Python / FastMCP)
	- Exposes high-level tools to AI agents and clients.
	- Background monitor reads Arduino status:
		- `TIMER:REMAINING:<secs>`, `COUNTDOWN:FINISHED`, `CLOCK:LCD:HH:MM:SS`, `DISTANCE:<cm>`.
	- Executes queued actions on triggers (`timer_zero`, `time_equals`, `distance_less_than`, `distance_update`).

- `master_control.ino` (Arduino firmware)
	- Non-blocking `loop()` orchestrates LED, buzzer, ultrasonic, LCD (clock/stopwatch/static), TM1637 (clock/stopwatch/countdown).
	- Serial protocol: `DEVICE:ACTION:VALUE` (e.g., `LED:BLINK:500`, `TM1637:COUNTDOWN:90`).

- `master_control.py` (Async CLI controller)
	- Human-driven test harness for commands, menus, clocks/timers.
## Hardware Stack

- LCD I2C 16x2 (`LiquidCrystal_I2C`) — default address `0x27` (try `0x3F` if needed)
- TM1637 4-digit 7-segment (`TM1637Display`)
- Ultrasonic sensor: TRIG=7, ECHO=6
- Buzzer: pin 13
- Built-in LED: `LED_BUILTIN`
- Wiring:
	- LCD I2C: SCL=10, SDA=11
	- TM1637: CLK=8, DIO=9
## Key Features

- Live displays:
	- LCD (16x2): live clock (`lcd_show_current_time`), stopwatch (`lcd_start_stopwatch`), static lines, backlight control.
	- TM1637 7-segment: live clock (`display_current_time`), live countdown (`display_timer`), stopwatch, static time/number, brightness.
- Actuators: `led_on/off/blink/toggle`, `buzzer_on/off/beep`.
- Sensors: Ultrasonic `start/stop/read`; live distance streaming to LCD (`show_live_ultrasonic_on_lcd`).
- Conditional automation (background-triggered):
	- `when_timer_finishes(then_action, params)`
	- `when_time_equals("HH:MM:SS", then_action, params)` — requires LCD clock.
	- `when_distance_less_than(cm, then_action, params)` — requires ultrasonic.
	- Actions include `buzzer_beep`, `start_timer("MM:SS")`, `led_blink`, `display_message("Line1|Line2")`.
# Arduino Master Control (Arduino-MCP)

AI-controlled automation platform for Arduino peripherals with live clocks, countdown timers, proximity sensing, and conditional triggers — enabling complex multi-step scenarios without manual supervision.

## Overview

Arduino-MCP bridges Python AI agents (via FastMCP) with an Arduino-based hardware stack to execute real-world actions, react to time and sensor events, and chain behaviors (e.g., “start a timer, then beep, then start another timer at a specific clock time”). The firmware uses non-blocking loops so displays and sensors update live on-device, while the Python server provides high-level tools and a background monitor that triggers actions automatically.

## Requirements

- Windows with Arduino connected (adjust COM port; default `COM6`).
- Python 3.10+ and `pyserial`; FastMCP is used by `arduino_mcp_server.py`.
- Arduino libraries: `LiquidCrystal_I2C`, `TM1637Display`.

## Setup

1) Flash the firmware:
- Open `master_control.ino` in Arduino IDE.
- Verify wiring and install libraries (`LiquidCrystal_I2C`, `TM1637Display`).
- Upload to your board.

2) Configure Python:
- Ensure COM port in `arduino_mcp_server.py` and `master_control.py` matches your board (default `COM6`).
 - Install Python dependencies (PowerShell): `pip install pyserial fastmcp`