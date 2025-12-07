"""
Arduino Master Control MCP Server
FastMCP server for AI-controlled Arduino automation with complex scenario support

CRITICAL: AI SCENARIO ANALYSIS & EXECUTION STRATEGY
====================================================
When given complex scenarios, AI MUST:
1. ANALYZE the user's prompt for temporal relationships ("when X then Y")
2. IDENTIFY all required actions and their triggers
3. SEQUENCE operations using conditional tools
4. CHAIN actions automatically without user intervention

CONDITIONAL EXECUTION FRAMEWORK:
- when_timer_finishes() → Execute action when countdown reaches 0
- when_time_equals() → Execute action at specific clock time  
- when_distance_less_than() → Execute action when object too close
- Actions execute AUTOMATICALLY in background, no polling needed!

EXAMPLE SCENARIO ANALYSIS:
User: "Start 90-sec timer, when done buzz, at 7:15 start 2-min timer"
AI Analysis:
  1. display_timer(1, 30) → Start first timer
  2. when_timer_finishes("buzzer_beep", "1000") → Auto-buzz at end
  3. lcd_show_current_time() → Show clock for time trigger
  4. when_time_equals("07:15:00", "start_timer", "02:00") → Auto-start at 7:15

DEVICES:
- LCD (16x2 text): lcd_show_current_time(), lcd_start_stopwatch(), lcd_write_line1/2()
- 7-Segment (4-digit): display_timer(), display_current_time(), display_start_stopwatch()
- LED: led_on/off/blink(), Buzzer: buzzer_on/off/beep()
- Ultrasonic: ultrasonic_start/stop/read(), show_live_ultrasonic_on_lcd()

TIME MODES:
- Clock = Actual PC time (14:30:45) - lcd_show_current_time() / display_current_time()
- Stopwatch = Count up from 00:00 - lcd_start_stopwatch() / display_start_stopwatch()  
- Timer = Count down to 00:00 - display_timer(min, sec)

AI: ALWAYS analyze user intent, identify triggers, and use conditional tools for automation!
"""

from fastmcp import FastMCP
import serial
import asyncio
import threading
from datetime import datetime
from typing import Optional
import time
import re

# Configuration
COM_PORT = "COM6"
BAUD_RATE = 9600

# Global Arduino connection
arduino_connection = None
connection_lock = asyncio.Lock()

# Global state tracking (updated by background monitor)
arduino_state = {
    "timer_remaining": 0,
    "timer_active": False,
    "clock_time": None,
    "distance": 0.0,
    "last_update": time.time()
}

# Background monitoring thread
monitor_thread = None
monitor_running = False

# Conditional actions queue
pending_actions = []

# Initialize FastMCP server
mcp = FastMCP("Arduino Master Control", dependencies=["pyserial"])

def get_arduino():
    """Get or create Arduino serial connection"""
    global arduino_connection
    if arduino_connection is None or not arduino_connection.is_open:
        try:
            arduino_connection = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.5)
            time.sleep(2)  # Wait for Arduino reset
        except serial.SerialException as e:
            raise Exception(f"Failed to connect to Arduino on {COM_PORT}: {e}")
    return arduino_connection

def send_command(command: str) -> str:
    """Send command to Arduino and get response"""
    arduino = get_arduino()
    try:
        arduino.write(f"{command}\n".encode())
        time.sleep(0.05)  # Small delay for Arduino to process
        
        # Read response if available
        if arduino.in_waiting > 0:
            response = arduino.readline().decode('utf-8').strip()
            return response
        return "OK"
    except Exception as e:
        return f"ERROR: {e}"

def start_background_monitor():
    """Start background thread to monitor Arduino status messages"""
    global monitor_thread, monitor_running
    
    if monitor_running:
        return
    
    monitor_running = True
    monitor_thread = threading.Thread(target=monitor_arduino_status, daemon=True)
    monitor_thread.start()

def stop_background_monitor():
    """Stop background monitoring thread"""
    global monitor_running
    monitor_running = False

def monitor_arduino_status():
    """Background thread function to continuously read Arduino status"""
    global arduino_state, pending_actions
    
    while monitor_running:
        try:
            arduino = get_arduino()
            if arduino and arduino.in_waiting > 0:
                line = arduino.readline().decode('utf-8').strip()
                
                # Parse status messages from Arduino
                if line.startswith("TIMER:REMAINING:"):
                    remaining = int(line.split(':')[2])
                    arduino_state["timer_remaining"] = remaining
                    arduino_state["timer_active"] = True
                    arduino_state["last_update"] = time.time()
                    
                elif line.startswith("COUNTDOWN:FINISHED"):
                    arduino_state["timer_remaining"] = 0
                    arduino_state["timer_active"] = False
                    arduino_state["last_update"] = time.time()
                    
                    # Execute pending actions triggered by timer completion
                    for action in pending_actions[:]:
                        if action.get("trigger") == "timer_zero":
                            execute_action(action)
                            pending_actions.remove(action)
                    
                elif line.startswith("CLOCK:LCD:"):
                    time_str = line.split(':', 2)[2]
                    arduino_state["clock_time"] = time_str
                    arduino_state["last_update"] = time.time()
                    
                    # Check time-based triggers
                    for action in pending_actions[:]:
                        if action.get("trigger") == "time_equals":
                            if time_str == action.get("target_time"):
                                execute_action(action)
                                pending_actions.remove(action)
                    
                elif line.startswith("DISTANCE:"):
                    distance = float(line.split(':')[1])
                    arduino_state["distance"] = distance
                    arduino_state["last_update"] = time.time()
                    
                    # Update LCD if distance monitoring is active
                    for action in pending_actions[:]:
                        if action.get("trigger") == "distance_update":
                            send_command(f"LCD:LINE2:{distance:.2f} cm       ")
                    
                    # Check distance-based triggers
                    for action in pending_actions[:]:
                        if action.get("trigger") == "distance_less_than":
                            if distance < action.get("target_distance"):
                                execute_action(action)
                                pending_actions.remove(action)
            
            time.sleep(0.05)  # Small delay to avoid CPU spinning
        except Exception as e:
            time.sleep(0.5)  # Longer delay on error

def execute_action(action):
    """Execute a pending action"""
    action_type = action.get("action_type")
    params = action.get("params", {})
    
    try:
        if action_type == "buzzer_beep":
            send_command(f"BUZZER:BEEP:{params.get('duration', 1000)}")
        elif action_type == "start_timer":
            minutes = params.get("minutes", 0)
            seconds = params.get("seconds", 0)
            total_seconds = minutes * 60 + seconds
            send_command(f"TM1637:COUNTDOWN:{total_seconds}")
        elif action_type == "led_blink":
            send_command(f"LED:BLINK:{params.get('interval', 1000)}")
        elif action_type == "display_message":
            send_command(f"LCD:LINE1:{params.get('line1', '')}")
            send_command(f"LCD:LINE2:{params.get('line2', '')}")
        elif action_type == "custom_command":
            send_command(params.get("command", ""))
    except Exception as e:
        print(f"Error executing action: {e}")

# Start monitoring when module loads
start_background_monitor()

# ============================================================================
# LED CONTROL TOOLS
# ============================================================================

@mcp.tool()
def led_on() -> str:
    """
    Turn the built-in LED ON (solid light, stays on continuously).
    This turns the LED to a steady ON state.
    Use this when you want the LED to stay on without blinking.
    """
    response = send_command("LED:ON")
    return "LED turned ON (solid, continuous)"

@mcp.tool()
def led_off() -> str:
    """
    Turn the built-in LED completely OFF.
    This stops any blinking and turns the LED off completely.
    Use this to turn off the LED or stop it from blinking.
    """
    response = send_command("LED:OFF")
    return "LED turned OFF"

@mcp.tool()
def led_blink(interval_ms: int = 500) -> str:
    """
    Make the LED blink continuously ON/OFF at the specified interval.
    The LED will keep blinking until you call led_off() or led_on().
    
    Examples:
    - interval_ms=500: Normal blinking (on for 500ms, off for 500ms)
    - interval_ms=100: Fast blinking
    - interval_ms=1000: Slow blinking
    
    Args:
        interval_ms: Time in milliseconds for each ON and OFF cycle (default: 500ms)
    """
    response = send_command(f"LED:BLINK:{interval_ms}")
    return f"LED is now blinking continuously at {interval_ms}ms intervals (call led_off to stop)"

@mcp.tool()
def led_toggle() -> str:
    """
    Toggle the LED state - if it's ON, turn it OFF; if it's OFF, turn it ON.
    This is a one-time toggle, not continuous blinking.
    Use this to flip the current LED state once.
    """
    response = send_command("LED:TOGGLE")
    return "LED state toggled (one-time flip)"

# ============================================================================
# BUZZER CONTROL TOOLS
# ============================================================================

@mcp.tool()
def buzzer_on() -> str:
    """
    Turn the buzzer ON continuously (constant sound).
    WARNING: This will keep buzzing until you call buzzer_off().
    Use this for continuous alarms or alerts.
    For short beeps, use buzzer_beep() instead.
    """
    response = send_command("BUZZER:ON")
    return "Buzzer turned ON (continuous sound - call buzzer_off to stop)"

@mcp.tool()
def buzzer_off() -> str:
    """
    Turn the buzzer completely OFF.
    This stops any continuous buzzing or beeping.
    Use this to silence the buzzer.
    """
    response = send_command("BUZZER:OFF")
    return "Buzzer turned OFF (silent)"

@mcp.tool()
def buzzer_beep(duration_ms: int = 100) -> str:
    """
    Make the buzzer beep ONCE for a specific duration, then automatically stop.
    This is a single beep that turns off by itself - no need to call buzzer_off().
    Perfect for notifications, alerts, or sound effects.
    
    Examples:
    - duration_ms=100: Quick beep
    - duration_ms=300: Medium beep
    - duration_ms=1000: Long beep (1 second)
    
    Args:
        duration_ms: How long the beep lasts in milliseconds (default: 100ms)
    """
    response = send_command(f"BUZZER:BEEP:{duration_ms}")
    return f"Buzzer beeped once for {duration_ms}ms (automatically stopped)"

# ============================================================================
# LCD CONTROL TOOLS
# ============================================================================

@mcp.tool()
def lcd_write_line1(text: str) -> str:
    """
    Write static text to LCD line 1 (the TOP line).
    This writes literal text - it does NOT show a clock or update automatically.
    The text stays on the screen until you clear it or write new text.
    Maximum 16 characters (text is truncated if longer).
    
    Examples:
    - lcd_write_line1("Hello World") → shows "Hello World" on top line
    - lcd_write_line1("Temperature") → shows "Temperature" on top line
    
    IMPORTANT: This shows STATIC TEXT ONLY, not live data.
    For a live updating clock on LCD, use lcd_clock() instead.
    
    Args:
        text: The static text to display on line 1 (max 16 chars)
    """
    text = text[:16]  # Truncate to 16 chars
    response = send_command(f"LCD:LINE1:{text}")
    return f"LCD Line 1 now shows static text: '{text}'"

@mcp.tool()
def lcd_write_line2(text: str) -> str:
    """
    Write static text to LCD line 2 (the BOTTOM line).
    This writes literal text - it does NOT show a clock or update automatically.
    The text stays on the screen until you clear it or write new text.
    Maximum 16 characters (text is truncated if longer).
    
    Examples:
    - lcd_write_line2("22.5 Celsius") → shows "22.5 Celsius" on bottom line
    - lcd_write_line2("Press START") → shows "Press START" on bottom line
    
    IMPORTANT: This shows STATIC TEXT ONLY, not live data.
    
    Args:
        text: The static text to display on line 2 (max 16 chars)
    """
    text = text[:16]  # Truncate to 16 chars
    response = send_command(f"LCD:LINE2:{text}")
    return f"LCD Line 2 now shows static text: '{text}'"

@mcp.tool()
def lcd_clear() -> str:
    """
    Clear the ENTIRE LCD display (both line 1 and line 2).
    This erases all text from the LCD screen, leaving it blank.
    Use this to reset the display before showing new information.
    """
    response = send_command("LCD:CLEAR")
    return "LCD completely cleared (both lines now blank)"

@mcp.tool()
def lcd_backlight_on() -> str:
    """
    Turn the LCD backlight ON (makes the screen bright and easy to read).
    This controls the LCD backlight, not the text.
    The backlight stays on until you turn it off.
    """
    response = send_command("LCD:BACKLIGHT:ON")
    return "LCD backlight turned ON (screen is now bright)"

@mcp.tool()
def lcd_backlight_off() -> str:
    """
    Turn the LCD backlight OFF (makes the screen dim or dark).
    The text is still there, but harder to see without the backlight.
    This saves power or reduces brightness.
    """
    response = send_command("LCD:BACKLIGHT:OFF")
    return "LCD backlight turned OFF (screen is now dim)"

@mcp.tool()
def lcd_display_message(line1: str, line2: str = "") -> str:
    """
    Display static text on BOTH LCD lines at once.
    This is a convenience function to write to both lines in one command.
    Both lines show STATIC TEXT that doesn't update automatically.
    
    Examples:
    - lcd_display_message("Welcome", "User 123") → Line 1: "Welcome", Line 2: "User 123"
    - lcd_display_message("Temperature", "22.5 C") → Line 1: "Temperature", Line 2: "22.5 C"
    
    IMPORTANT: This shows STATIC TEXT ONLY on both lines.
    For a live updating clock, use lcd_clock() instead.
    
    Args:
        line1: Static text for top line (max 16 characters)
        line2: Static text for bottom line (max 16 characters, optional)
    """
    line1 = line1[:16]
    line2 = line2[:16]
    send_command(f"LCD:LINE1:{line1}")
    if line2:
        send_command(f"LCD:LINE2:{line2}")
    return f"LCD now shows: Line 1='{line1}' | Line 2='{line2}'"

@mcp.tool()
def lcd_show_current_time() -> str:
    """
    Display ACTUAL SYSTEM TIME as a LIVE CLOCK on the LCD screen (16x2 character display).
    
    ✅ DISPLAYS REAL PC TIME (not a stopwatch!)
    
    Display format:
    - Line 1: "HH:MM:SS" (actual PC time like 14:30:45, updates every second)
    - Line 2: "Date Day" (like "07/12/2025 Sat")
    
    The Arduino continuously updates the clock display in the background!
    This shows your ACTUAL COMPUTER TIME synchronized from Python.
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    IMPORTANT: This is a CLOCK (real time), NOT a stopwatch!
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    - Clock = Shows actual PC time (14:30:45) → THIS FUNCTION
    - Stopwatch = Counts up from 00:00:00 → Use lcd_start_stopwatch()
    - Timer = Counts down to 00:00:00 → No LCD countdown yet (use 7-segment)
    
    When to use this:
    - "Show live clock on LCD" → YES, use this
    - "Display current time on LCD" → YES, use this
    - "Show time on LCD screen" → YES, use this
    - "What time is it on LCD" → YES, use this
    
    To stop the clock:
    - Call lcd_clear() to stop and clear
    - Call lcd_write_line1() or lcd_write_line2() to stop and show custom text
    
    When NOT to use:
    - User asks for stopwatch → Use lcd_start_stopwatch() instead
    - User asks for 7-segment display → Use display_current_time() instead
    
    Returns: Confirmation that live clock started (updates automatically on Arduino)
    """
    now = datetime.now()
    hours = now.strftime("%H")
    minutes = now.strftime("%M")
    seconds = now.strftime("%S")
    date = now.strftime("%m/%d/%Y")
    day = now.strftime("%a")
    
    # Send actual time to Arduino: LCD:CLOCK:HH:MM:SS:Date:Day
    command = f"LCD:CLOCK:{hours}:{minutes}:{seconds}:{date}:{day}"
    send_command(command)
    return f"✅ LIVE CLOCK STARTED on LCD showing ACTUAL TIME: {hours}:{minutes}:{seconds} {date} {day}. The time will update automatically every second. To stop: use lcd_clear() or write new text."

@mcp.tool()
def lcd_start_stopwatch() -> str:
    """
    Start a STOPWATCH on the LCD screen (counts UP from 00:00:00).
    
    Display format:
    - Line 1: "Stopwatch:"
    - Line 2: "HH:MM:SS" (counting up from 00:00:00)
    
    This is different from a clock:
    - Clock = Shows actual PC time (14:30:45) → Use lcd_show_current_time()
    - Stopwatch = Counts up from 00:00:00 → THIS FUNCTION
    
    The stopwatch starts immediately when called and counts up automatically.
    
    When to use this:
    - "Start a stopwatch on LCD" → YES, use this
    - "Count up from zero on LCD" → YES, use this
    - "Timer counting up on LCD" → YES, use this
    
    To stop the stopwatch:
    - Call lcd_stop_stopwatch() to stop
    - Call lcd_clear() to stop and clear
    
    Returns: Confirmation that stopwatch started
    """
    send_command("LCD:STOPWATCH:START")
    return "✅ STOPWATCH STARTED on LCD! Counting up from 00:00:00. To stop: use lcd_stop_stopwatch() or lcd_clear()."

@mcp.tool()
def lcd_stop_stopwatch() -> str:
    """
    Stop the stopwatch on the LCD screen.
    This stops the counting and clears the display.
    
    Returns: Confirmation that stopwatch stopped
    """
    send_command("LCD:STOPWATCH:STOP")
    return "Stopwatch stopped and LCD cleared."

# ============================================================================
# TM1637 7-SEGMENT DISPLAY TOOLS
# ============================================================================

@mcp.tool()
def display_number(number: int) -> str:
    """
    Display a static number on the 4-digit 7-segment display.
    This shows a NUMBER, not time - just plain digits without colons.
    The number stays on screen until you clear it or show something else.
    
    Examples:
    - display_number(1234) → shows "1234"
    - display_number(42) → shows "  42" (right-aligned)
    - display_number(-99) → shows " -99"
    
    IMPORTANT: This shows STATIC NUMBERS ONLY, not live updating time.
    For showing actual time, use display_current_time() instead.
    
    Range: -999 to 9999 (4 digits maximum)
    
    Args:
        number: The number to display (-999 to 9999)
    """
    if number < -999 or number > 9999:
        return "Error: Number must be between -999 and 9999"
    response = send_command(f"TM1637:NUM:{number}")
    return f"7-segment display now shows static number: {number}"

@mcp.tool()
def display_time(time_hhmm: str) -> str:
    """
    Display a STATIC time on the 7-segment display in HH:MM format with colon.
    This shows a fixed time that does NOT update - the colon blinks but time stays same.
    
    Examples:
    - display_time("1430") → shows "14:30" (2:30 PM) with blinking colon
    - display_time("0915") → shows "09:15" (9:15 AM) with blinking colon
    - display_time("2359") → shows "23:59" (11:59 PM) with blinking colon
    
    IMPORTANT: This displays a FIXED time you specify, NOT the current time.
    For showing the ACTUAL current time that updates, use display_current_time() instead.
    
    Args:
        time_hhmm: Time in HHMM format (4 digits: HH=hours 00-23, MM=minutes 00-59)
    """
    if len(time_hhmm) != 4 or not time_hhmm.isdigit():
        return "Error: Time must be exactly 4 digits in HHMM format (example: '1430' for 2:30 PM)"
    response = send_command(f"TM1637:NUM:{time_hhmm}")
    return f"7-segment display now shows static time: {time_hhmm[:2]}:{time_hhmm[2:]} (fixed, not updating)"

@mcp.tool()
def display_current_time() -> str:
    """
    Display ACTUAL SYSTEM TIME as a LIVE CLOCK on the 7-SEGMENT DISPLAY (4-digit numeric display).
    
    ✅ DISPLAYS REAL PC TIME (not a stopwatch!)
    
    Display format: HH:MM (24-hour format with blinking colon between digits)
    Example: 14:30 (shows actual PC time like 2:30 PM)
    
    The Arduino continuously updates the clock display every second!
    This shows your ACTUAL COMPUTER TIME synchronized from Python.
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    IMPORTANT: This is a CLOCK (real time), NOT a stopwatch!
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    - Clock = Shows actual PC time (14:30) → THIS FUNCTION
    - Stopwatch = Counts up from 00:00 → Use display_start_stopwatch()
    - Timer = Counts down to 00:00 → Use display_timer()
    
    DISPLAY SELECTION GUIDE:
    - 7-segment display = THIS TOOL (numeric display, 4 digits)
    - LCD display = Use lcd_show_current_time() (text display, 2 lines)
    - "Show live clock" = THIS TOOL (when referring to 7-segment)
    - "Show time on LCD" = Use lcd_show_current_time() (different device!)
    
    When to use this:
    - "Show live clock on 7-segment display" → YES, use this
    - "Display current time on the numeric display" → YES, use this
    - "Show actual time on display" → YES, use this
    - "What time is it on 7-segment" → YES, use this
    
    To stop the clock:
    - Call display_clear() to stop and clear
    - Call display_number() to stop and show a number
    - Call display_timer() to stop clock and start countdown
    
    When NOT to use:
    - User asks for stopwatch → Use display_start_stopwatch() instead
    - User asks for LCD → Use lcd_show_current_time() instead
    - User wants countdown timer → Use display_timer() instead
    
    Returns: Confirmation that live clock started (updates automatically on Arduino)
    """
    now = datetime.now()
    hours = now.strftime("%H")
    minutes = now.strftime("%M")
    
    # Send actual time to Arduino: TM1637:CLOCK:HH:MM
    command = f"TM1637:CLOCK:{hours}:{minutes}"
    send_command(command)
    return f"✅ LIVE CLOCK STARTED on 7-segment display showing ACTUAL TIME: {hours}:{minutes}. The time will update automatically every second. To stop: use display_clear() or show a number."

@mcp.tool()
def display_start_stopwatch() -> str:
    """
    Start a STOPWATCH on the 7-segment display (counts UP from 00:00).
    
    Display format: HH:MM (counting up from 00:00)
    Example: 00:00 → 00:01 → 00:02 → ... → 23:59
    
    This is different from a clock:
    - Clock = Shows actual PC time (14:30) → Use display_current_time()
    - Stopwatch = Counts up from 00:00 → THIS FUNCTION
    - Timer = Counts down to 00:00 → Use display_timer()
    
    The stopwatch starts immediately when called and counts up automatically.
    
    When to use this:
    - "Start a stopwatch on 7-segment" → YES, use this
    - "Count up from zero on display" → YES, use this
    - "Timer counting up" → YES, use this
    
    To stop the stopwatch:
    - Call display_stop_stopwatch() to stop
    - Call display_clear() to stop and clear
    
    Returns: Confirmation that stopwatch started
    """
    send_command("TM1637:STOPWATCH:START")
    return "✅ STOPWATCH STARTED on 7-segment display! Counting up from 00:00 in HH:MM format. To stop: use display_stop_stopwatch() or display_clear()."

@mcp.tool()
def display_stop_stopwatch() -> str:
    """
    Stop the stopwatch on the 7-segment display.
    This stops the counting and clears the display.
    
    Returns: Confirmation that stopwatch stopped
    """
    send_command("TM1637:STOPWATCH:STOP")
    return "Stopwatch stopped and 7-segment display cleared."

@mcp.tool()
def display_clear() -> str:
    """
    Clear the 7-segment display completely.
    This turns off all segments, leaving the display blank/dark.
    Use this to reset the display before showing new information.
    """
    response = send_command("TM1637:CLEAR")
    return "7-segment display cleared (all segments off, display is blank)"

@mcp.tool()
def display_brightness(level: int) -> str:
    """
    Set the brightness level of the 7-segment display.
    This controls how bright or dim the display appears.
    
    Examples:
    - level=0: Dimmest (but still visible)
    - level=7: Medium brightness
    - level=15: Maximum brightness (brightest)
    
    The brightness setting persists until changed again.
    
    Args:
        level: Brightness level from 0 (dimmest) to 15 (brightest)
    """
    level = max(0, min(15, level))
    response = send_command(f"TM1637:BRIGHTNESS:{level}")
    return f"7-segment display brightness set to {level}/15 (0=dimmest, 15=brightest)"

@mcp.tool()
def display_timer(minutes: int, seconds: int) -> str:
    """
    Start a LIVE COUNTDOWN TIMER on the 7-segment display in MM:SS format.
    
    ✅ THIS NOW WORKS! The countdown updates automatically every second on Arduino!
    
    Display format: MM:SS with blinking colon
    The countdown automatically counts down to 00:00, then beeps 3 times!
    
    Examples:
    - display_timer(5, 30) → starts at "05:30" and counts down automatically
    - display_timer(0, 45) → starts at "00:45" and counts down to "00:00"
    - display_timer(10, 0) → starts at "10:00" (10 minutes)
    
    The timer counts down automatically: 05:00 → 04:59 → 04:58 → ... → 00:01 → 00:00 → BEEP!
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    HOW IT WORKS (Same strategy as LED blinking):
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Arduino runs a loop that updates the countdown every second!
    When it reaches 00:00, it beeps 3 times automatically.
    
    This is a TRUE live countdown - not static display!
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    IMPORTANT: This is a LIVE COUNTDOWN TIMER that actually counts down.
    Use this for timers, countdowns, or time-based tasks.
    
    Different from:
    - display_current_time() which shows a live clock counting UP
    - display_time() which shows fixed time that doesn't change
    - countdown_display() which shows static countdown (old function)
    
    To stop the countdown:
    - Call display_clear() to stop and clear
    - Call display_number() to stop and show a number
    - Call display_current_time() to stop and start a clock
    
    Args:
        minutes: Minutes for countdown (0-99)
        seconds: Seconds for countdown (0-59)
    """
    if minutes < 0 or minutes > 99 or seconds < 0 or seconds > 59:
        return "Error: Minutes must be 0-99 and seconds must be 0-59"
    
    total_seconds = minutes * 60 + seconds
    response = send_command(f"TM1637:COUNTDOWN:{total_seconds}")
    
    return f"✅ LIVE COUNTDOWN STARTED: {minutes:02d}:{seconds:02d} on 7-segment display! The timer will count down automatically every second (just like LED blinking). When it reaches 00:00, it will beep 3 times! To stop: use display_clear() or show something else."

# ============================================================================
# ULTRASONIC SENSOR TOOLS
# ============================================================================

@mcp.tool()
def ultrasonic_start() -> str:
    """
    Start CONTINUOUS distance monitoring mode on the ultrasonic sensor.
    In this mode, the Arduino continuously reads distance and can trigger actions.
    The sensor keeps measuring until you call ultrasonic_stop().
    
    Use cases:
    - Continuous object detection
    - Proximity monitoring
    - Automatic alerts when objects get close
    
    To get the actual distance values, use ultrasonic_read() after starting.
    To stop continuous monitoring, use ultrasonic_stop().
    """
    response = send_command("ULTRA:START")
    return "Ultrasonic sensor started in CONTINUOUS monitoring mode (call ultrasonic_stop to end)"

@mcp.tool()
def ultrasonic_stop() -> str:
    """
    Stop continuous distance monitoring on the ultrasonic sensor.
    This ends the continuous monitoring mode started by ultrasonic_start().
    The sensor will no longer read distances until you start it again.
    """
    response = send_command("ULTRA:STOP")
    return "Ultrasonic sensor stopped (continuous monitoring ended)"

@mcp.tool()
def ultrasonic_read() -> str:
    """
    Get a SINGLE distance reading from the ultrasonic sensor.
    This measures the distance to the nearest object once and returns the result.
    
    Returns: Distance in centimeters (cm)
    
    Range: Typically 2cm to 400cm (depending on object reflectivity)
    - Very close: < 10cm
    - Close: 10-30cm
    - Medium: 30-100cm
    - Far: > 100cm
    
    Use cases:
    - Check distance once without continuous monitoring
    - Measure how far away an object is
    - Detect if something is in range
    
    Example results:
    - "Distance: 15.32 cm" - Object is 15cm away
    - "Distance: 245.67 cm" - Object is 2.45 meters away
    
    For continuous monitoring, use ultrasonic_start() instead.
    """
    arduino = get_arduino()
    send_command("ULTRA:READ")
    time.sleep(0.1)  # Wait for reading
    
    # Read response
    if arduino.in_waiting > 0:
        response = arduino.readline().decode('utf-8').strip()
        if response.startswith("ULTRA:"):
            try:
                distance = float(response.split(':')[1])
                if distance < 10:
                    proximity = "VERY CLOSE"
                elif distance < 30:
                    proximity = "CLOSE"
                elif distance < 100:
                    proximity = "MEDIUM"
                else:
                    proximity = "FAR"
                return f"Distance: {distance:.2f} cm ({proximity})"
            except:
                pass
    return "Error reading distance from ultrasonic sensor"

# ============================================================================
# SYSTEM TOOLS
# ============================================================================

@mcp.tool()
def explain_display_capabilities() -> str:
    """
    Get detailed information about display capabilities and limitations.
    
    ✅ UPDATED: Live clocks and countdown timers NOW WORK!
    
    This tool explains what is and isn't possible with the Arduino displays.
    Call this when you need to understand display capabilities.
    
    CRITICAL INFORMATION:
    ═══════════════════════════════════════════════════════════════════
    
    1. TWO SEPARATE DISPLAYS:
       • LCD Display (16x2): Text display, 2 lines × 16 characters
       • 7-Segment Display: Numeric display, 4 digits with colon
    
    2. ✅ LIVE FEATURES NOW AVAILABLE:
       ✓ Live updating clocks (Arduino handles updates in loop)
       ✓ Live countdown timers (automatically count down to 00:00)
       ✓ LED-style continuous operation (same strategy as LED blink)
       ✓ Auto-beep when countdown reaches zero
    
    3. HOW IT WORKS:
       • Arduino runs loop() function continuously (like LED blink)
       • Clocks update every second automatically
       • Countdown decreases every second automatically
       • No need for repeated Python function calls!
    
    4. CORRECT TOOL SELECTION:
       • "Show live clock on LCD" → lcd_show_current_time() ✅ LIVE!
       • "Show live clock on 7-segment" → display_current_time() ✅ LIVE!
       • "Start countdown timer" → display_timer() ✅ LIVE COUNTDOWN!
       • "Show static time" → display_time() (fixed, doesn't update)
    
    5. TO STOP LIVE FEATURES:
       ✓ LCD clock: lcd_clear() or write new text
       ✓ 7-segment clock: display_clear() or show a number
       ✓ Countdown: display_clear() or start clock
    
    ═══════════════════════════════════════════════════════════════════
    
    Use this tool to understand the NEW live capabilities!
    """
    return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARDUINO DISPLAY CAPABILITIES & LIMITATIONS (UPDATED!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📺 AVAILABLE DISPLAYS:
1. LCD Display (16x2)
   • Type: Character text display
   • Size: 2 lines, 16 characters per line
   • Shows: Letters, numbers, symbols
   • Functions: lcd_show_current_time() ✅ LIVE CLOCK!

2. 7-Segment Display (TM1637)
   • Type: Numeric LED display
   • Size: 4 digits with colon
   • Shows: Numbers (0-9) and time format (HH:MM)
   • Functions: display_current_time() ✅ LIVE CLOCK!
                display_timer() ✅ LIVE COUNTDOWN!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ NEW FEATURES - LIVE UPDATES NOW WORK!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ LIVE CLOCKS AVAILABLE:
• LCD live clock updates every second automatically
• 7-segment live clock updates every second automatically
• Arduino handles updates in loop (like LED blinking)
• No repeated Python calls needed!

✅ LIVE COUNTDOWN TIMER:
• Counts down automatically every second
• Shows MM:SS format
• Beeps 3 times when reaching 00:00
• Runs until stopped or countdown finishes

✅ HOW IT WORKS:
Arduino's loop() function runs continuously and updates displays.
Same strategy as LED blinking - once started, runs automatically!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 CORRECT RESPONSES TO USER REQUESTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User: "Show time on LCD"
✓ Correct: Call lcd_show_current_time() → LIVE CLOCK! ✅
✗ Wrong: Call lcd_write_line1("current time") ← Shows literal text!

User: "Show live clock"
✓ Correct: "Starting live clock now! It will update automatically 
           every second on the display."
✗ Wrong: "Clocks don't work..." ← THEY DO NOW!

User: "Start a 5 minute countdown"
✓ Correct: Call display_timer(5, 0) → LIVE COUNTDOWN! ✅
✗ Wrong: Using display_time() ← That's static, not countdown!

User: "Time should update automatically"
✓ Correct: "Starting live clock now! The Arduino will update it 
           automatically every second, just like the LED blinks."
✗ Wrong: Saying it's not possible ← IT IS NOW!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 KEY TAKEAWAY FOR AI ASSISTANTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ LIVE CLOCKS AND COUNTDOWNS NOW WORK!
Use lcd_show_current_time(), display_current_time(), and display_timer()
for automatic updating displays. They work just like LED blinking!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

@mcp.tool()
def get_system_status() -> str:
    """
    Get the current status of ALL connected devices and peripherals.
    This returns a comprehensive report showing:
    - LED status (on/off/blinking)
    - Buzzer status (on/off)
    - LCD display content
    - 7-segment display content
    - Ultrasonic sensor state (active/inactive)
    
    Use this to check what state all devices are in.
    """
    response = send_command("STATUS")
    return "System status requested - all device states reported"

@mcp.tool()
def test_connection() -> str:
    """
    Test if the Arduino is properly connected and responding.
    This verifies the serial connection is working.
    
    Returns:
    - Success: If Arduino is connected and ready
    - Error: If Arduino is not connected or not responding
    
    Use this to troubleshoot connection problems.
    """
    try:
        arduino = get_arduino()
        if arduino and arduino.is_open:
            return f"✓ SUCCESS: Arduino is connected and ready on {COM_PORT}"
        else:
            return f"✗ ERROR: Arduino is not connected on {COM_PORT}"
    except Exception as e:
        return f"✗ CONNECTION ERROR: {e}"

@mcp.tool()
def all_off() -> str:
    """
    Turn OFF and CLEAR everything - complete system reset.
    This performs a full shutdown of all devices:
    - LED: Turned off (stops blinking if active)
    - Buzzer: Silenced completely
    - LCD: Cleared (both lines blank)
    - 7-segment display: Cleared (all segments off)
    - Ultrasonic sensor: Stopped (ends continuous monitoring)
    
    Use this to:
    - Reset everything to clean state
    - Stop all ongoing actions
    - Clear all displays
    - Emergency stop for all devices
    
    This is like a "reset all" or "turn everything off" command.
    """
    send_command("LED:OFF")
    send_command("BUZZER:OFF")
    send_command("LCD:CLEAR")
    send_command("TM1637:CLEAR")
    send_command("ULTRA:STOP")
    return "✓ ALL DEVICES OFF: LED off, buzzer silent, displays cleared, sensor stopped"

# ============================================================================
# COMPLEX SCENARIOS (Multi-device operations)
# ============================================================================

@mcp.tool()
def welcome_message(name: str) -> str:
    """
    Display a personalized welcome message with sound effect.
    This performs a multi-device welcome sequence:
    1. Clears LCD screen
    2. Shows "Welcome!" on LCD line 1
    3. Shows the person's name on LCD line 2
    4. Beeps buzzer once as a greeting sound
    
    Perfect for greeting users, visitors, or starting a session.
    
    Example:
    - welcome_message("John") → LCD shows "Welcome!" and "John", beeps once
    - welcome_message("Dr. Smith") → LCD shows "Welcome!" and "Dr. Smith", beeps once
    
    Args:
        name: The name to display in the welcome message (max 16 characters)
    """
    send_command("LCD:CLEAR")
    send_command(f"LCD:LINE1:Welcome!")
    send_command(f"LCD:LINE2:{name[:16]}")
    send_command("BUZZER:BEEP:200")
    return f"Welcome sequence completed: 'Welcome! {name}' displayed on LCD with greeting beep"

@mcp.tool()
def proximity_alert() -> str:
    """
    Check distance with ultrasonic sensor and trigger automatic alerts based on proximity.
    This is an intelligent multi-device alert system that:
    
    VERY CLOSE (< 10cm):
    - Buzzer: ON continuously (alarm)
    - LED: Fast blinking (100ms)
    - LCD: "WARNING! Too Close!"
    - Status: ⚠️ CRITICAL ALERT
    
    CLOSE (10-30cm):
    - LED: Solid ON (warning)
    - LCD: "Caution" + distance
    - Status: ⚠ Warning
    
    SAFE (> 30cm):
    - All devices OFF
    - LCD: "Clear" + distance
    - Status: ✓ All Clear
    
    Use cases:
    - Automatic proximity detection
    - Collision prevention
    - Safety monitoring
    - Object detection with visual/audio feedback
    
    Returns: Current distance and alert status with actions taken
    """
    arduino = get_arduino()
    send_command("ULTRA:READ")
    time.sleep(0.1)
    
    distance = -1
    if arduino.in_waiting > 0:
        response = arduino.readline().decode('utf-8').strip()
        if response.startswith("ULTRA:"):
            try:
                distance = float(response.split(':')[1])
            except:
                pass
    
    if distance < 0:
        return "ERROR: Could not read distance from ultrasonic sensor"
    elif distance < 10:
        send_command("BUZZER:ON")
        send_command("LED:BLINK:100")
        send_command(f"LCD:LINE1:WARNING!")
        send_command(f"LCD:LINE2:Too Close!")
        return f"⚠️ CRITICAL ALERT! Object at {distance:.2f}cm - Buzzer ON, LED fast blinking, warning displayed"
    elif distance < 30:
        send_command("BUZZER:OFF")
        send_command("LED:ON")
        send_command(f"LCD:LINE1:Caution")
        send_command(f"LCD:LINE2:{distance:.1f} cm")
        return f"⚠ Warning: Object at {distance:.2f}cm - LED ON, caution displayed"
    else:
        send_command("LED:OFF")
        send_command("BUZZER:OFF")
        send_command(f"LCD:LINE1:Clear")
        send_command(f"LCD:LINE2:{distance:.1f} cm")
        return f"✓ All Clear - Distance: {distance:.2f}cm - No threats detected"

@mcp.tool()
def countdown_display(seconds: int) -> str:
    """
    Display a countdown timer on the 7-segment display and beep when finished.
    This shows MM:SS format countdown (minutes:seconds with colon).
    
    Examples:
    - countdown_display(90) → shows "01:30" (1 minute 30 seconds)
    - countdown_display(45) → shows "00:45" (45 seconds)
    - countdown_display(300) → shows "05:00" (5 minutes)
    
    The display shows static countdown format - for live counting,
    this needs to be called repeatedly or use timer logic.
    
    Use cases:
    - Cooking timers
    - Workout intervals
    - Countdown clocks
    - Time-based challenges
    
    Note: This shows the INITIAL countdown value. For a live countdown
    that updates every second, additional timer logic is needed.
    
    Args:
        seconds: Total seconds for countdown (0-5940, which is 0-99 minutes)
    """
    if seconds < 0 or seconds > 5940:
        return "Error: Seconds must be between 0 and 5940 (99 minutes max)"
    
    mins = seconds // 60
    secs = seconds % 60
    time_str = f"{mins:02d}{secs:02d}"
    send_command(f"TM1637:NUM:{time_str}")
    return f"Countdown initialized: {mins:02d}:{secs:02d} displayed on 7-segment ({seconds} total seconds)"

@mcp.tool()
def display_info(title: str, value: str, show_number: Optional[int] = None) -> str:
    """
    Display information on BOTH LCD and 7-segment display simultaneously.
    This is a multi-display information system that shows:
    - LCD line 1: Title/label
    - LCD line 2: Value/data
    - 7-segment: Optional number (if provided)
    
    Perfect for showing measurements, status info, or data with labels.
    
    Examples:
    - display_info("Temperature", "22.5 C", 22) 
      → LCD: "Temperature" / "22.5 C", Display: "22"
    
    - display_info("Speed", "65 km/h", 65)
      → LCD: "Speed" / "65 km/h", Display: "65"
    
    - display_info("Status", "Running")
      → LCD: "Status" / "Running", Display: unchanged
    
    Use cases:
    - Sensor readings with labels
    - Status information
    - Measurements with units
    - Data visualization across multiple displays
    
    Args:
        title: Label/title for LCD line 1 (max 16 chars)
        value: Data/value for LCD line 2 (max 16 chars)
        show_number: Optional number for 7-segment display (-999 to 9999)
    """
    send_command(f"LCD:LINE1:{title[:16]}")
    send_command(f"LCD:LINE2:{value[:16]}")
    if show_number is not None:
        send_command(f"TM1637:NUM:{show_number}")
        return f"Multi-display info: LCD shows '{title}' / '{value}', 7-segment shows {show_number}"
    else:
        return f"Multi-display info: LCD shows '{title}' / '{value}'"

@mcp.tool()
def celebration() -> str:
    """
    Trigger a FUN celebration sequence using all devices! 🎉
    This is an exciting multi-device show that performs:
    1. LCD: Shows "Celebration!" and "Hooray!"
    2. LED: Fast blinking (200ms intervals)
    3. Buzzer: Three quick beeps in sequence
    4. 7-segment: Shows "8888" (all segments lit)
    
    Perfect for:
    - Success notifications
    - Achievement unlocks
    - Party mode
    - Fun demonstrations
    - Winning events
    - Completion celebrations
    
    Duration: ~1 second
    All devices activate simultaneously for maximum effect!
    
    Use this when something awesome happens!
    """
    send_command("LCD:LINE1:Celebration!")
    send_command("LCD:LINE2:Hooray!")
    send_command("LED:BLINK:200")
    
    # Three beeps in sequence
    for i in range(3):
        send_command("BUZZER:BEEP:150")
        time.sleep(0.3)
    
    send_command("TM1637:NUM:8888")
    return "🎉 CELEBRATION SEQUENCE ACTIVATED! LCD message, LED blinking, 3 beeps, display lit - party time!"

# ============================================================================
# CONDITIONAL EXECUTION TOOLS (Complex Scenarios)
# ============================================================================

@mcp.tool()
def when_timer_finishes(then_action: str, action_params: Optional[str] = "") -> str:
    """
    AUTO-EXECUTE action when countdown timer reaches 0. Critical for complex scenarios!
    
    AI USAGE: Call this IMMEDIATELY after display_timer() to set up automatic actions.
    Background monitor detects timer completion and executes WITHOUT further commands.
    
    Actions: "buzzer_beep", "start_timer", "led_blink", "display_message"
    
    Examples:
    - when_timer_finishes("buzzer_beep", "1000") → Beep 1 sec when timer→0
    - when_timer_finishes("start_timer", "02:00") → Start 2-min timer when current timer→0
    - when_timer_finishes("led_blink", "500") → Flash LED when timer→0
    
    SCENARIO: "5-min timer then beep then 2-min timer"
    AI SHOULD CALL:
      display_timer(5, 0)
      when_timer_finishes("buzzer_beep", "1000")
      when_timer_finishes("start_timer", "02:00")
    
    Returns: Confirmation of queued action
    """
    global pending_actions
    
    # Parse action parameters
    params = {}
    if then_action == "buzzer_beep":
        params = {"duration": int(action_params) if action_params else 1000}
    elif then_action == "start_timer":
        # Format: MM:SS
        if ":" in action_params:
            parts = action_params.split(":")
            params = {"minutes": int(parts[0]), "seconds": int(parts[1])}
        else:
            return "Error: Timer format must be MM:SS (e.g., '02:00' for 2 minutes)"
    elif then_action == "led_blink":
        params = {"interval": int(action_params) if action_params else 1000}
    elif then_action == "display_message":
        # Format: Line1|Line2
        if "|" in action_params:
            parts = action_params.split("|")
            params = {"line1": parts[0], "line2": parts[1]}
        else:
            params = {"line1": action_params, "line2": ""}
    
    # Add to pending actions
    action = {
        "trigger": "timer_zero",
        "action_type": then_action,
        "params": params
    }
    pending_actions.append(action)
    
    return f"✅ CONDITIONAL ACTION SET: When timer reaches 0 → Execute '{then_action}' with params: {params}. The system will monitor and execute automatically!"

@mcp.tool()
def when_time_equals(target_time: str, then_action: str, action_params: Optional[str] = "") -> str:
    """
    AUTO-EXECUTE action when clock reaches specific time. For time-based automation!
    
    REQUIRES: LCD clock must be running! Call lcd_show_current_time() FIRST.
    
    AI USAGE: Use for "at X time" or "when clock shows X" scenarios.
    Format: HH:MM:SS (24-hour, e.g., "14:30:00" for 2:30 PM, "07:15:00" for 7:15 AM)
    
    Actions: Same as when_timer_finishes()
    
    SCENARIO: "Show clock, at 7:15 buzz and start timer"
    AI SHOULD CALL:
      lcd_show_current_time()
      when_time_equals("07:15:00", "buzzer_beep", "2000")
      when_time_equals("07:15:00", "start_timer", "02:00")
    
    Returns: Confirmation of time-based trigger
    """
    global pending_actions
    
    # Validate time format
    if not re.match(r'^\d{2}:\d{2}:\d{2}$', target_time):
        return "Error: Time must be in HH:MM:SS format (e.g., '14:30:00')"
    
    # Parse action parameters (same as when_timer_finishes)
    params = {}
    if then_action == "buzzer_beep":
        params = {"duration": int(action_params) if action_params else 1000}
    elif then_action == "start_timer":
        if ":" in action_params:
            parts = action_params.split(":")
            params = {"minutes": int(parts[0]), "seconds": int(parts[1])}
        else:
            return "Error: Timer format must be MM:SS"
    elif then_action == "led_blink":
        params = {"interval": int(action_params) if action_params else 1000}
    elif then_action == "display_message":
        if "|" in action_params:
            parts = action_params.split("|")
            params = {"line1": parts[0], "line2": parts[1]}
        else:
            params = {"line1": action_params, "line2": ""}
    
    # Add to pending actions
    action = {
        "trigger": "time_equals",
        "target_time": target_time,
        "action_type": then_action,
        "params": params
    }
    pending_actions.append(action)
    
    return f"✅ TIME-BASED TRIGGER SET: When clock reaches {target_time} → Execute '{then_action}'. Make sure LCD clock is running (lcd_show_current_time)!"

@mcp.tool()
def when_distance_less_than(distance_cm: float, then_action: str, action_params: Optional[str] = "") -> str:
    """
    AUTO-EXECUTE action when object gets too close. For proximity automation!
    
    REQUIRES: Ultrasonic must be active! Call ultrasonic_start() FIRST.
    
    AI USAGE: Use for "if closer than X" or "when distance < X" scenarios.
    Trigger executes ONCE when threshold crossed, then removed from queue.
    
    SCENARIO: "Monitor distance, beep if < 10cm"
    AI SHOULD CALL:
      ultrasonic_start()
      when_distance_less_than(10, "buzzer_beep", "500")
    
    Returns: Confirmation of proximity trigger
    """
    global pending_actions
    
    # Parse action parameters
    params = {}
    if then_action == "buzzer_beep":
        params = {"duration": int(action_params) if action_params else 1000}
    elif then_action == "start_timer":
        if ":" in action_params:
            parts = action_params.split(":")
            params = {"minutes": int(parts[0]), "seconds": int(parts[1])}
        else:
            return "Error: Timer format must be MM:SS"
    elif then_action == "led_blink":
        params = {"interval": int(action_params) if action_params else 1000}
    elif then_action == "display_message":
        if "|" in action_params:
            parts = action_params.split("|")
            params = {"line1": parts[0], "line2": parts[1]}
        else:
            params = {"line1": action_params, "line2": ""}
    
    # Add to pending actions
    action = {
        "trigger": "distance_less_than",
        "target_distance": distance_cm,
        "action_type": then_action,
        "params": params
    }
    pending_actions.append(action)
    
    return f"✅ PROXIMITY TRIGGER SET: When distance < {distance_cm}cm → Execute '{then_action}'. Make sure ultrasonic is active (ultrasonic_start)!"

@mcp.tool()
def show_live_ultrasonic_on_lcd() -> str:
    """
    Display LIVE distance readings on LCD (auto-updates every 500ms).
    
    Combines ultrasonic_start() + automatic LCD updates.
    LCD shows: "Distance:" / "XX.XX cm"
    
    Returns: Confirmation
    """
    # Start ultrasonic monitoring
    send_command("ULTRA:START")
    
    # The background monitor will receive DISTANCE: messages
    # and we'll update the LCD in the monitoring thread
    
    # Add a special action that continuously updates LCD with distance
    global pending_actions
    pending_actions.append({
        "trigger": "distance_update",
        "action_type": "update_lcd_distance",
        "params": {}
    })
    
    send_command("LCD:LINE1:Distance:")
    
    return "✅ LIVE ULTRASONIC MONITORING STARTED! LCD will continuously show distance. Arduino sends distance every 500ms and LCD updates automatically. To stop: lcd_clear() or ultrasonic_stop()"

@mcp.tool()
def get_current_status() -> str:
    """
    Get real-time system status: timer, clock, distance, pending actions.
    Use to verify what's running and what actions are queued.
    """
    global arduino_state, pending_actions
    
    status = []
    status.append("=" * 60)
    status.append("ARDUINO SYSTEM STATUS")
    status.append("=" * 60)
    
    # Timer status
    if arduino_state["timer_active"]:
        mins = arduino_state["timer_remaining"] // 60
        secs = arduino_state["timer_remaining"] % 60
        status.append(f"⏱ Timer: ACTIVE - {mins:02d}:{secs:02d} remaining")
    else:
        status.append("⏱ Timer: INACTIVE")
    
    # Clock status
    if arduino_state["clock_time"]:
        status.append(f"🕐 Clock: {arduino_state['clock_time']}")
    else:
        status.append("🕐 Clock: NOT RUNNING")
    
    # Distance status
    if arduino_state["distance"] > 0:
        status.append(f"📏 Distance: {arduino_state['distance']:.2f} cm")
    else:
        status.append("📏 Distance: NOT MONITORING")
    
    # Pending actions
    status.append(f"\n⚡ Pending Conditional Actions: {len(pending_actions)}")
    for i, action in enumerate(pending_actions, 1):
        trigger = action.get("trigger")
        action_type = action.get("action_type")
        
        if trigger == "timer_zero":
            status.append(f"  {i}. When timer → 0: Execute '{action_type}'")
        elif trigger == "time_equals":
            target = action.get("target_time")
            status.append(f"  {i}. When clock = {target}: Execute '{action_type}'")
        elif trigger == "distance_less_than":
            target = action.get("target_distance")
            status.append(f"  {i}. When distance < {target}cm: Execute '{action_type}'")
    
    status.append(f"\n📊 Last Update: {time.time() - arduino_state['last_update']:.1f} seconds ago")
    status.append("=" * 60)
    
    return "\n".join(status)

@mcp.tool()
def clear_all_pending_actions() -> str:
    """
    Clear all queued conditional actions. Devices keep running normally.
    Use to reset automation system or cancel pending triggers.
    """
    global pending_actions
    count = len(pending_actions)
    pending_actions.clear()
    return f"✅ Cleared {count} pending conditional action(s). All timers, clocks, and sensors still running normally."

if __name__ == "__main__":
    mcp.run()
