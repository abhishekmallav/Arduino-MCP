"""
Master Control System for Arduino Peripherals
Supports: LCD I2C, TM1637 Display, Ultrasonic Sensor, Buzzer, Built-in LED

This is an async implementation that allows simultaneous control of multiple devices.
"""

import asyncio
import serial
import sys
from datetime import datetime
import aioconsole

# Change COM port to match your Arduino
COM_PORT = "COM6"
BAUD_RATE = 9600

class ArduinoController:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.arduino = None
        self.running = False
        self.ultrasonic_active = False
        self.clock_active = False
        self.timer_active = False
        self.timer_seconds = 0
        self.lcd_clock_active = False
        
    async def connect(self):
        """Establish connection to Arduino"""
        try:
            self.arduino = serial.Serial(self.port, self.baudrate, timeout=0.1)
            await asyncio.sleep(2)  # Wait for Arduino reset
            print(f"✓ Connected to Arduino on {self.port}")
            return True
        except serial.SerialException as e:
            print(f"✗ Error: Could not open serial port {self.port}")
            print(f"  Details: {e}")
            return False
    
    def send_command(self, command):
        """Send command to Arduino"""
        if self.arduino:
            try:
                self.arduino.write(f"{command}\n".encode())
                return True
            except Exception as e:
                print(f"✗ Error sending command: {e}")
                return False
        return False
    
    async def read_responses(self):
        """Continuously read responses from Arduino"""
        while self.running:
            try:
                if self.arduino and self.arduino.in_waiting > 0:
                    line = self.arduino.readline().decode('utf-8').strip()
                    if line:
                        await self.handle_response(line)
            except Exception as e:
                print(f"✗ Error reading response: {e}")
            await asyncio.sleep(0.01)
    
    async def handle_response(self, response):
        """Handle responses from Arduino"""
        if response.startswith("OK:"):
            # Acknowledgment - optionally log
            pass
        elif response.startswith("ULTRA:"):
            # Ultrasonic reading
            try:
                distance = float(response.split(':')[1])
                if distance > 0:
                    print(f"  📏 Distance: {distance:.2f} cm      ", end='\r')
            except:
                pass
        elif response.startswith("ERROR:"):
            print(f"\n✗ {response}")
        elif response.startswith("STATUS:"):
            print(f"  {response}")
    
    # Device Control Methods
    
    def led_on(self):
        """Turn LED on"""
        self.send_command("LED:ON")
        print("✓ LED: ON")
    
    def led_off(self):
        """Turn LED off"""
        self.send_command("LED:OFF")
        print("✓ LED: OFF")
    
    def led_blink(self, interval=500):
        """Blink LED with specified interval (ms)"""
        self.send_command(f"LED:BLINK:{interval}")
        print(f"✓ LED: Blinking at {interval}ms interval")
    
    def led_toggle(self):
        """Toggle LED state"""
        self.send_command("LED:TOGGLE")
        print("✓ LED: Toggled")
    
    def buzzer_on(self):
        """Turn buzzer on"""
        self.send_command("BUZZER:ON")
        print("✓ Buzzer: ON")
    
    def buzzer_off(self):
        """Turn buzzer off"""
        self.send_command("BUZZER:OFF")
        print("✓ Buzzer: OFF")
    
    def buzzer_beep(self, duration=100):
        """Beep buzzer for specified duration (ms)"""
        self.send_command(f"BUZZER:BEEP:{duration}")
        print(f"✓ Buzzer: Beep for {duration}ms")
    
    def lcd_write(self, line, text):
        """Write text to LCD line (1 or 2)"""
        self.send_command(f"LCD:LINE{line}:{text}")
        print(f"✓ LCD Line {line}: {text}")
    
    def lcd_clear(self):
        """Clear LCD display"""
        self.send_command("LCD:CLEAR")
        print("✓ LCD: Cleared")
    
    def lcd_backlight(self, state):
        """Control LCD backlight (ON/OFF)"""
        self.send_command(f"LCD:BACKLIGHT:{state}")
        print(f"✓ LCD Backlight: {state}")
    
    def display_number(self, number):
        """Display number on TM1637"""
        self.send_command(f"TM1637:NUM:{number}")
        print(f"✓ Display: {number}")
    
    def display_clear(self):
        """Clear TM1637 display"""
        self.send_command("TM1637:CLEAR")
        print("✓ Display: Cleared")
    
    def display_brightness(self, level):
        """Set display brightness (0-15)"""
        level = max(0, min(15, level))
        self.send_command(f"TM1637:BRIGHTNESS:{level}")
        print(f"✓ Display Brightness: {level}")
    
    def ultrasonic_start(self):
        """Start continuous ultrasonic readings"""
        self.send_command("ULTRA:START")
        self.ultrasonic_active = True
        print("✓ Ultrasonic: Started")
    
    def ultrasonic_stop(self):
        """Stop ultrasonic readings"""
        self.send_command("ULTRA:STOP")
        self.ultrasonic_active = False
        print("✓ Ultrasonic: Stopped")
    
    def ultrasonic_read(self):
        """Get single ultrasonic reading"""
        self.send_command("ULTRA:READ")
    
    def get_status(self):
        """Get status of all devices"""
        self.send_command("STATUS")
    
    # High-level Functions
    
    async def display_clock(self):
        """Display current time on TM1637"""
        self.clock_active = True
        print("✓ Clock: Started on TM1637")
        while self.clock_active and self.running:
            now = datetime.now()
            time_str = now.strftime("%H%M")
            self.send_command(f"TM1637:NUM:{time_str}")
            await asyncio.sleep(1)
    
    async def display_countdown(self, minutes, seconds):
        """Display countdown timer on TM1637"""
        self.timer_active = True
        total_seconds = minutes * 60 + seconds
        print(f"✓ Timer: Started {minutes:02d}:{seconds:02d}")
        
        while total_seconds >= 0 and self.timer_active and self.running:
            mins = total_seconds // 60
            secs = total_seconds % 60
            time_str = f"{mins:02d}{secs:02d}"
            self.send_command(f"TM1637:NUM:{time_str}")
            
            if total_seconds == 0:
                print("\n✓ Timer: Finished!")
                # Beep 3 times
                for _ in range(3):
                    self.buzzer_beep(300)
                    await asyncio.sleep(0.5)
                break
            
            total_seconds -= 1
            await asyncio.sleep(1)
        
        self.timer_active = False
    
    async def lcd_clock(self):
        """Display date and time on LCD"""
        self.lcd_clock_active = True
        print("✓ LCD Clock: Started")
        while self.running and self.lcd_clock_active:
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")
            date_str = now.strftime("%d/%m/%Y %a")
            self.send_command(f"LCD:LINE1:{time_str}")
            self.send_command(f"LCD:LINE2:{date_str}")
            await asyncio.sleep(1)
        self.lcd_clock_active = False
    
    def stop_clock(self):
        """Stop clock display"""
        self.clock_active = False
        print("✓ Clock: Stopped")
    
    def stop_timer(self):
        """Stop countdown timer"""
        self.timer_active = False
        print("✓ Timer: Stopped")
    
    def stop_lcd_clock(self):
        """Stop LCD clock display"""
        self.lcd_clock_active = False
        print("✓ LCD Clock: Stopped")
    
    def close(self):
        """Close connection"""
        self.running = False
        if self.arduino:
            self.arduino.close()
            print("\n✓ Serial connection closed")

async def show_menu():
    """Display command menu"""
    menu = """
╔═══════════════════════════════════════════════════════════════╗
║           Arduino Master Control System                       ║
╠═══════════════════════════════════════════════════════════════╣
║  LED Commands:                                                ║
║    led on / led off / led blink [interval]                    ║
║                                                                ║
║  Buzzer Commands:                                             ║
║    buzzer on / buzzer off / buzzer beep [duration]            ║
║                                                                ║
║  LCD Commands:                                                ║
║    lcd 1:<text> / lcd 2:<text> / lcd clear                    ║
║    lcd clock (show date/time) / lcd stop                      ║
║                                                                ║
║  Display (TM1637) Commands:                                   ║
║    display <number> / display clear                           ║
║    display clock / display timer:<MM:SS> / display stop       ║
║    display brightness <0-15>                                  ║
║                                                                ║
║  Ultrasonic Commands:                                         ║
║    ultra start / ultra stop / ultra read                      ║
║                                                                ║
║  Other:                                                       ║
║    status / help / exit                                       ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(menu)

async def process_command(controller, cmd):
    """Process user commands"""
    cmd = cmd.strip().lower()
    parts = cmd.split()
    
    if not parts:
        return True
    
    device = parts[0]
    
    try:
        # LED Commands
        if device == "led":
            if len(parts) < 2:
                print("✗ Usage: led on/off/blink/toggle")
            elif parts[1] == "on":
                controller.led_on()
            elif parts[1] == "off":
                controller.led_off()
            elif parts[1] == "blink":
                interval = int(parts[2]) if len(parts) > 2 else 500
                controller.led_blink(interval)
            elif parts[1] == "toggle":
                controller.led_toggle()
        
        # Buzzer Commands
        elif device == "buzzer":
            if len(parts) < 2:
                print("✗ Usage: buzzer on/off/beep")
            elif parts[1] == "on":
                controller.buzzer_on()
            elif parts[1] == "off":
                controller.buzzer_off()
            elif parts[1] == "beep":
                duration = int(parts[2]) if len(parts) > 2 else 100
                controller.buzzer_beep(duration)
        
        # LCD Commands
        elif device == "lcd":
            if len(parts) < 2:
                print("✗ Usage: lcd 1:<text> / lcd 2:<text> / lcd clear / lcd clock / lcd stop")
            elif parts[1] == "clear":
                controller.lcd_clear()
            elif parts[1] == "clock":
                asyncio.create_task(controller.lcd_clock())
            elif parts[1] == "stop":
                controller.stop_lcd_clock()
                await asyncio.sleep(0.1)  # Give task time to stop
            elif parts[1].startswith("1:"):
                text = cmd.split("1:", 1)[1]
                controller.lcd_write(1, text)
            elif parts[1].startswith("2:"):
                text = cmd.split("2:", 1)[1]
                controller.lcd_write(2, text)
        
        # Display Commands
        elif device == "display":
            if len(parts) < 2:
                print("✗ Usage: display <number>/clear/clock/timer:<MM:SS>/stop/brightness")
            elif parts[1] == "clear":
                controller.display_clear()
            elif parts[1] == "clock":
                controller.stop_timer()
                asyncio.create_task(controller.display_clock())
            elif parts[1].startswith("timer:"):
                controller.stop_clock()
                time_part = parts[1].split(":", 1)[1]
                mins, secs = map(int, time_part.split(":"))
                asyncio.create_task(controller.display_countdown(mins, secs))
            elif parts[1] == "stop":
                controller.stop_clock()
                controller.stop_timer()
            elif parts[1] == "brightness":
                level = int(parts[2]) if len(parts) > 2 else 15
                controller.display_brightness(level)
            else:
                try:
                    number = int(parts[1])
                    controller.display_number(number)
                except ValueError:
                    print("✗ Invalid number")
        
        # Ultrasonic Commands
        elif device == "ultra":
            if len(parts) < 2:
                print("✗ Usage: ultra start/stop/read")
            elif parts[1] == "start":
                controller.ultrasonic_start()
            elif parts[1] == "stop":
                controller.ultrasonic_stop()
            elif parts[1] == "read":
                controller.ultrasonic_read()
        
        # Other Commands
        elif device == "status":
            controller.get_status()
        elif device == "help":
            await show_menu()
        elif device in ["exit", "quit"]:
            return False
        else:
            print(f"✗ Unknown command: {device}")
            print("  Type 'help' for available commands")
    
    except Exception as e:
        print(f"✗ Error processing command: {e}")
    
    return True

async def main():
    """Main async function"""
    print("\n" + "="*65)
    print("  Arduino Master Control System")
    print("="*65)
    
    controller = ArduinoController(COM_PORT, BAUD_RATE)
    
    if not await controller.connect():
        print("\n✗ Failed to connect. Check:")
        print("  - Arduino is connected")
        print("  - Correct COM port")
        print("  - No other program is using the port")
        return
    
    controller.running = True
    
    # Start response reader task
    reader_task = asyncio.create_task(controller.read_responses())
    
    await show_menu()
    
    try:
        while controller.running:
            try:
                # Non-blocking input
                user_input = await aioconsole.ainput("\n> ")
                if not await process_command(controller, user_input):
                    break
            except EOFError:
                break
    except KeyboardInterrupt:
        print("\n\n✓ Interrupted by user")
    finally:
        controller.close()
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Program terminated")
