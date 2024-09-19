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

bus = can.interface.Bus(channel='com6', bustype='seeedstudio', bitrate=500000)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('127.0.0.1', 4567))
    
# Track time for each function separately
start_time_100ms = time.time()
start_time_10ms = time.time()
start_time_5s = time.time()
#0x3de
id_counter = 0x3e0
random_data = [0,0,0,0,0,0,0,0]
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
iat = 85
oil_pressure = 50

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

abs_active = False
abs_fault = False

front_right_tire = 28
front_left_tire = 29
rear_left_tire = 30
rear_right_tire = 31
# Global variable for steering wheel control data
steering_wheel_data = [0,0,0,0,0,0,0,0]

def gui_thread():
    def set_steering_wheel_data(data):
        global steering_wheel_data
        steering_wheel_data = data

    def reset_steering_wheel_data(event):
        global steering_wheel_data
        steering_wheel_data = [0,0,0,0,0,0,0,0]

    def set_random_data(data):
        global random_data
        random_data = data
        print(random_data)

    def reset_random_data(event):
        global random_data
        random_data = [0,0,0,0,0,0,0,0]

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

    button_rand = tk.Button(root, text="Randomize")
    button_rand.bind("<ButtonPress>", lambda event: set_random_data([random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255)]))
    button_rand.grid(row=2, column=2, padx=5, pady=5)

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
def format_text_to_can_chunks(text, input):
    firstline = True
    # Convert each character to its ASCII hex representation interleaved with "00"
    formatted_text = [f"00 {ord(char):02X}" for char in text]
    
    # Flatten list into a single array of hex numbers
    formatted_text = ' '.join(formatted_text).split()

    # Each chunk should fit in 6 hex values (3 characters)
    chunks = [formatted_text[i:i + 6] for i in range(0, len(formatted_text), 6)]

    # Create CAN message chunks with the start_byte and a line code that increments by 0x10 each message
    can_chunks = []

    #up until here, it works and generates data[2]-[7] correctly.
    start_byte = len(chunks)
    for i, chunk in enumerate(chunks):
        # Start byte with the incremented line code
        can_data = [(start_byte - (i+1))*0x10]

        can_data.append((firstline*0x40)+input)
        # Add up to 6 hex values to fit within 8 bytes total, padding with 0 if necessary
        can_data.extend(int(chunk[j], 16) if j < len(chunk) else 0 for j in range(6))
        firstline = False
        can_chunks.append(can_data[:8])  # Ensure each CAN message is exactly 8 bytes

    # Add an end-of-message frame (all zeros)
    can_chunks.append([0x00] * 8)
    return can_chunks

def send_can_messages(bus, can_id, chunks):
    for chunk in chunks:
        message = can.Message(arbitration_id=can_id, data=chunk, is_extended_id=False)
        try:
            bus.send(message)
            #print(message)
        except can.CanError as e:
            print(f"Failed to send message: {e}")

def send_display_text(bus, text, text_type='artist'):

    if text_type == 'artist':
        start_byte = 0x02  # Artist
    elif text_type == 'song' or "title":
        start_byte = 0x03  # Song Title
    elif text_type == 'input':
        start_byte = 0x01  # Radio Input Name
    else:
        raise ValueError("Invalid text type. Use 'artist', 'song', or 'input'.")

    can_chunks = format_text_to_can_chunks(text, start_byte)
    send_can_messages(bus, 0x328, can_chunks)


while True:
    current_time = time.time()
    #print(gearSelector)
    match gearSelector:
            case b'D':
                gearByte = 0x08
            case b'N':
                gearByte = 0x06
            case b'0':
                gearByte = 0x06
            case b'R':
                gearByte = 0x04
            case b'-':
                gearByte = 0x04
            case b'P':
                gearByte = 0x02
            case _:
                gearByte = 0x0a
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
        fuelvalue = int(fuel * 2.55)
        send_display_text(bus, "EyePhone69", text_type="input")
        send_display_text(bus, "NiggasAndJews", text_type="song")

        messages_100ms = [
            can.Message(arbitration_id=0x112, data=[ # ign
                (ignition*0x4)+0b10000000,0], is_extended_id=False),
            can.Message(arbitration_id=0x1d0, data=[ # airbag
                0,0,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x12c, data=[ # power steering
                0,0,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x180, data=[ # battery light
                iat,int(coolant_temp *1.1)+32,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x22f, data=[ # electronic throttle control
                0,0,0,0,0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x278, data=[ # red background
                0,0,0,0,0b00100000,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x200, data=[ # fuel
                0xa4,0x1c,0x0b,0x52,0x02+(fuelvalue&0xf),0x0a+(fuelvalue>>4),0x79,0xff], is_extended_id=False),
            can.Message(arbitration_id=0x304, data=[ # tpms
                lowpressure,0,0,front_left_tire,front_right_tire,rear_left_tire,rear_right_tire,35], is_extended_id=False),
            can.Message(arbitration_id=0x2a0, data=[ # mil, im not even gonna pretend to know what this equation does
                check_engine,0,oil_pressure,int(round(0x00 + (oil_temp + 40) * (0xC8 - 0x00) / (160 - (-40)))) if -40 <= oil_temp <= 160 else (0x00 if oil_temp < -40 else 0xC8),0,0,0,0], is_extended_id=False),
            can.Message(arbitration_id=0x334, data=[ # lights
                foglight*4,lowbeam,handbrake*128,(left_directional*64)+(right_directional*128),0,0,240,highbeam*4], is_extended_id=False),
            #can.Message(arbitration_id=0x3e1, data=[ # coolant enable (vehicle deatils bitmap) manual/auto bitmap for messages
            #    118,48,80,113,0x00,0x00,0x00,0xaa], is_extended_id=False),
            #can.Message(arbitration_id=0x3e4, data=[ # active dampening/ blindspot detection/ acc/fcw
            #    0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,0xaa,0xaa], is_extended_id=False),
            #can.Message(arbitration_id=0x3e8, data=[ #  vehicle deatils bitmap -- background red, bar/psi, gear appear/disappear, can get gear to stop blinking, SPEED WARNING 120??
            #    0x49,0x2c,0x22,0x21,0xbe,0x9e,0x13,0x10], is_extended_id=False),
            #can.Message(arbitration_id=0x3ea, data=[ #  vehicle deatils bitmap -- font of everything, changes from h/c to temps, 
            #    0x41,0x40,0x22,0x2b,0xcd,0x24,0x03,0xfc], is_extended_id=False),
            #can.Message(arbitration_id=0x3eb, data=[ #  vehicle deatils bitmap -- -FROM A CHALLENGER R/T
            #    0x40,0x00,0x0c,0x05,0x00,0x00,0x08,0xbb], is_extended_id=False),
            #can.Message(arbitration_id=0x3c9, data=[ #  vehicle deatils bitmap -- -FROM A CHALLENGER R/T
            #    0x81,0x48,0x00,0x00], is_extended_id=False),
            #can.Message(arbitration_id=0x330, data=[ # tc
            #    200,0,0,0,0,0,0,0], is_extended_id=False),
            #can.Message(arbitration_id=0x350, data=[ # time
            #    date.second,date.minute,date.hour,4,5,6,7,8], is_extended_id=False),
            can.Message(arbitration_id=id_counter, data=random_data, is_extended_id=False),
        ]
        
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
            can.Message(arbitration_id=0x2e0, data=[ # esc, mpg
                0,0,0,0,0x0e,0xcc,tc_off*8,(abs_active*8)+(abs_fault*4)+(tc_active*2)], is_extended_id=False),
            can.Message(arbitration_id=0x11c, data=[ # speed
                0x80,0,0,0,int(speed*1.8),0,0x10,0x66], is_extended_id=False),
            can.Message(arbitration_id=0x170, data=[ # gear
                random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),random.randint(0,255),gearByte,0], is_extended_id=False),
            can.Message(arbitration_id=0x22d, data=steering_wheel_data, is_extended_id=False), # Trip button
        ]

        for message in messages_10ms:
            bus.send(message)
            wpt.sleep(0.001)
        start_time_10ms = time.time()

    # Execute code every 5s
    elapsed_time_5s = current_time - start_time_5s
    if elapsed_time_5s >= 10:
        id_counter += 1
        print(hex(id_counter))
        if id_counter == 0x3ff:
            id_counter = 0x0
        '''
        rpm = random.randint(0,7000)
        speed = random.randint(0,80)
        abs_active = not abs_active
        tc_active = not tc_active
        left_directional = not left_directional
        right_directional = not right_directional
        check_engine = not check_engine
        handbrake = not handbrake
        highbeam = not highbeam
        lowbeam = not lowbeam
        
        '''
        start_time_5s = time.time()
        """
        #EVIC DISPLAY OF SONG NAME
        328 LINE CODES:              +-> 2=Artist, 3=Song Title,
                                     |   1=Radio Input Name
              4=Start of new line---+|
        Lines remaining----------+  ||
                                 |  ||
        can0  RX - -  328   [8]  30 42 00 42 00 6C 00 75   '0B.B.l.u' <--Artist
        can0  RX - -  328   [8]  20 02 00 65 00 46 00 6F   ' ..e.F.o'
        can0  RX - -  328   [8]  10 02 00 78 00 4D 00 75   '...x.M.u'
        can0  RX - -  328   [8]  00 02 .00 73 00 69 00 63   '...s.i.c'
        can0  RX - -  328   [8]  00 00 00 00 00 00 00 00   '........' <--END OF MESSAGE

        can0  RX - -  328   [8]  50 43 00 45 00 6C 00 65   'PC.E.l.e' <--Song Title
        can0  RX - -  328   [8]  40 03 00 63 00 74 00 72   '@..c.t.r'
        can0  RX - -  328   [8]  30 03 00 6F 00 20 00 50   '0..o. .P'
        can0  RX - -  328   [8]  20 03 00 65 00 72 00 66   ' ..e.r.f'
        can0  RX - -  328   [8]  10 03 00 65 00 63 00 74   '...e.c.t' <--TOO MANY CHARS
        can0  RX - -  328   [8]  00 03 00 6F 00 00 00 00   '...o....' <--WILL NOT SHOW
        can0  RX - -  328   [8]  00 00 00 00 00 00 00 00   '........' <--END OF MESSAGE

            Always transmit 8 bytes. Use "00" for any unused characters.
        """
