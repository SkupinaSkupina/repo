import serial
import struct

class AccelerometerModule:
    def __init__(self, port, baud_rate, timeout=1):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        """Attempt to establish a connection to the serial port."""
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            self.connected = True
            print(f"Connected to {self.port} at {self.baud_rate} baud")
        except serial.SerialException as e:
            self.connected = False
            print(f"No connection to {self.port}: {e}")

    def close(self):
        """Closes the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed")

    def read_packet(self):
        if self.ser and self.ser.is_open:
            try:
                data = self.ser.read(4)  # Attempt to read 4 bytes
                if len(data) == 4:
                    header, smer_voznje = struct.unpack('<HH', data)
                    return header, smer_voznje
                else:
                    return None  # Incomplete data, skip processing
            except serial.SerialTimeoutException:
                return None  # Handle timeouts gracefully
            except Exception as e:
                print(f"Error reading packet: {e}")
                return None
        return None

