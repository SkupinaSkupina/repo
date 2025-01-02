import serial
import struct
import time

SERIAL_PORT = 'COM3'
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")
except serial.SerialException as e:
    print(f"Failed to connect to {SERIAL_PORT}: {e}")
    exit(1)

try:
    while True:
        # Read 8 bytes from serial
        data = ser.read(4)
        if len(data) == 4:
            #print(f"Raw data: {data.hex()}")

            # Unpack the raw data with reversed header
            # First 2 bytes as `unsigned short` to avoid signed interpretation
            header, x= struct.unpack('<Hh', data)

            if header == 0xaaab:
                print(x)
            else:
                print(f"Invalid packet header: {hex(header)}")
        else:
            print("Incomplete data received")

        #time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting...")
finally:
    ser.close()
    print("Serial port closed")
