import time
import can
import random 
import socket
import struct
import select 
import threading
import tkinter as tk
import win_precise_time as wpt
from datetime import datetime

bus = can.interface.Bus(channel='com7', bustype='seeedstudio', bitrate=500000)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('127.0.0.1', 4567))
    
# Track time for each function separately
start_time_100ms = time.time()
start_time_10ms = time.time()
start_time_5s = time.time()

id_counter = 0
counter_4bit = 0

ignition = True
rpm = 780
speed = 0
gear = b'0'
gearSelector = b"P"
coolant_temp = 60
oil_temp = 90
fuel = 100
boost = 0

left_directional = False
lowpressure = False
right_directional = False
tc_off = False
tc_active = False
abs = False
cruise_control_active = False
cruise_control_speed = 0
handbrake = False
sport_mode = False
outside_temp = 72

foglight = False
rear_foglight = False
lowbeam = False 
highbeam = False
check_engine = False

hood = False
trunk = False
driver_door = False
passenger_door = False
driver_rear_door = False
passenger_rear_door = False

airbag = False
seatbelt = False
sos_call = False

# Global variable for steering wheel control data
steering_wheel_data = [0,0,0,0,0,0,0,0]

def gui_thread():
    def set_steering_wheel_data(data):
        global steering_wheel_data
        steering_wheel_data = data

    def reset_steering_wheel_data(event):
        global steering_wheel_data
        steering_wheel_data = [0,0,0,0,0,0,0,0]

    root = tk.Tk()
    root.title("LandRoverLR2")

    # Configure grid layout
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(1, weight=1)

    # Buttons arranged in their natural positions
    button_up = tk.Button(root, text="Up")
    button_up.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0, 0, 0, 0, 0, 0b00000100, 0, 0]))
    button_up.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_up.grid(row=0, column=1, padx=5, pady=5)

    button_left = tk.Button(root, text="Left")
    button_left.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0, 0, 0, 0, 0b00010000, 0, 0, 0]))
    button_left.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_left.grid(row=1, column=0, padx=5, pady=5)

    button_ok = tk.Button(root, text="OK")
    button_ok.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0, 0, 0, 0, 0, 0b00010000, 0, 0]))
    button_ok.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_ok.grid(row=1, column=1, padx=5, pady=5)

    button_right = tk.Button(root, text="Right")
    button_right.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0, 0, 0, 0, 0, 0b00000001, 0, 0]))
    button_right.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_right.grid(row=1, column=2, padx=5, pady=5)

    button_down = tk.Button(root, text="Down")
    button_down.bind("<ButtonPress>", lambda event: set_steering_wheel_data([0, 0, 0, 0, 0b01000000, 0, 0, 0]))
    button_down.bind("<ButtonRelease>", reset_steering_wheel_data)
    button_down.grid(row=2, column=1, padx=5, pady=5)

    root.mainloop()
# Start the GUI thread
gui_thread = threading.Thread(target=gui_thread)
gui_thread.start()

def receive():
    while True:
        try:
            message = bus.recv()
        except:
            print("Message error")

receive_thread = threading.Thread(target=receive)    
receive_thread.start()

while True:
    current_time = time.time()
    
    # Read from the socket if there is data to be read
    ready_to_read, _, _ = select.select([sock], [], [], 0)
    if sock in ready_to_read:
        data, _ = sock.recvfrom(256)
        packet = struct.unpack('2c7f2I3f', data)
        rpm = int(max(min(packet[3], 8000), 0))
        speed = packet[2] # Convert speed to km/h
        coolant_temp = int(packet[5])
        oil_temp = int(packet[8])
        fuel = int(packet[6]*100)
        gearSelector = packet[0]
        gear = packet[1]
        boost = packet[4]*14.5038
        # Parse other packet data (bitwise operations)
        shiftlight = (packet[10]>>0) & 1
        highbeam = (packet[10]>>1) & 1
        handbrake = (packet[10]>>2) & 1
        tc_active = (packet[10]>>3) & 1
        tc_off = (packet[10]>>4) & 1
        left_directional = (packet[10]>>5) & 1
        right_directional = (packet[10]>>6) & 1
        lowoilpressure = (packet[10]>>7) & 1
        battery = (packet[10]>>8) & 1
        abs_active = (packet[10]>>9) & 1
        abs_fault = False
        ignition = (packet[10]>>11) & 1
        lowpressure = (packet[10]>>12) & 1
        check_engine = (packet[10]>>13) & 1
        foglight = (packet[10]>>14) & 1
        lowbeam = (packet[10]>>15) & 1
        cruise_control_active = (packet[10]>>16) & 1
    
    # Send each message every 100ms
    elapsed_time_100ms = current_time - start_time_100ms
    if elapsed_time_100ms >= 0.1:
        date = datetime.now()
        match gearSelector:
            case b'N':
                gearByte = 2
            case b'R':
                gearByte = 1
            case b'P':
                gearByte = 0
            case _:
                gearByte = 3
        messages_100ms = [
            

            can.Message(arbitration_id=0x112, data=[ # ign
                ignition*0x4,0,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x1d0, data=[ # airbag
                0,0,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x180, data=[ # battery light
                0,0,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x2e0, data=[ # esc
                0,0,0,0,0,0,tc_off*8,(abs_active*8)+(not abs_fault*4)], is_extended_id=False),
            can.Message(arbitration_id=0x330, data=[ # tc
                0,0,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x2a0, data=[ # mil
                check_engine,0,0,id_counter,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x334, data=[ # lights
                foglight*4,0,handbrake*128,(left_directional*64)+(right_directional*128),0,0,240,highbeam*4], is_extended_id=False),
            can.Message(arbitration_id=id_counter, data=[
                random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255)], is_extended_id=False),
        ]
        
        # Update checksums and counters here
        counter_4bit = (counter_4bit + 1) % 16

        # Send Messages
        for message in messages_100ms:
            bus.send(message)
            wpt.sleep(0.001)
        start_time_100ms = time.time()

    # Execute code every 10ms
    elapsed_time_10ms = current_time - start_time_10ms
    if elapsed_time_10ms >= 0.01:  # 10ms
        messages_10ms = [
            can.Message(arbitration_id=0x108, data=[ # rpm
                int(rpm)>>8,int(rpm)&0xff,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x11c, data=[ # speed
                0,0,0,0,int(speed*1.8),0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x22d, data=steering_wheel_data, is_extended_id=False), # Trip button

        ]
        # Do checksums here

        for message in messages_10ms:
            bus.send(message)
            wpt.sleep(0.001)
        start_time_10ms = time.time()

    # Execute code every 5s
    elapsed_time_5s = current_time - start_time_5s
    if elapsed_time_5s >= 1:
        id_counter += 1
        #get message id counter, change it to zero, randomize the correct bit, after 3 seconds of brutefocing make it change it to the next bit
        print(hex(id_counter))
        if id_counter == 0x7ff:
            id_counter = 0
        
        start_time_5s = time.time()

receive_thread.join()

sock.close()
