import tkinter as tk
from tkinter import ttk
import can
import threading
import time

# Setup CAN interface
bus = can.interface.Bus(channel='com7', bustype='seeedstudio', bitrate=500000)

class CanBruteForcer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CAN Brute-Force Tool")
        self.geometry("600x700")  # Increased size for the new buttons

        # Variables for ID and data brute-forcing
        self.current_id = 0x000
        self.current_byte_index = 0
        self.current_bit_position = 0
        self.running = False
        self.toggle_state = False  # Tracks if the current bit is toggled on or off
        self.last_bit_change_time = time.time()
        self.last_send_time = time.time()
        self.auto_increment = tk.BooleanVar(value=True)  # Variable for auto increment checkbox
        self.bit_states = [[0] * 8 for _ in range(8)]  # 8 bytes of 8 bits each, all initialized to 0

        # GUI Elements
        self.create_widgets()

    def create_widgets(self):
        # Start/Stop Button
        self.start_button = ttk.Button(self, text="Start Brute-Force", command=self.toggle_bruteforce)
        self.start_button.pack(pady=10)

        # Status Label
        self.status_label = ttk.Label(self, text="Status: Stopped")
        self.status_label.pack(pady=10)

        # CAN ID Entry
        self.id_label = ttk.Label(self, text="Enter CAN ID (hex):")
        self.id_label.pack()
        self.id_entry = ttk.Entry(self, width=10)  
        self.id_entry.pack()
        self.id_entry.insert(0, "000")  # Default CAN ID

        # Apply ID Button
        self.apply_id_button = ttk.Button(self, text="Apply ID", command=self.apply_id)
        self.apply_id_button.pack(pady=5)

        # Manual Bit Increment/Decrement Buttons
        self.increment_button = ttk.Button(self, text="Increment Bit", command=self.increment_bit)
        self.increment_button.pack(pady=5)

        self.decrement_button = ttk.Button(self, text="Decrement Bit", command=self.decrement_bit)
        self.decrement_button.pack(pady=5)

        # Auto Increment Checkbox
        self.auto_increment_checkbox = ttk.Checkbutton(self, text="Auto Increment Bit", variable=self.auto_increment)
        self.auto_increment_checkbox.pack(pady=5)

        # Output Log
        self.output_text = tk.Text(self, height=10, width=60)  # Wider output box
        self.output_text.pack(pady=10)

        # Bit Toggle Frame
        self.bit_toggle_frame = ttk.LabelFrame(self, text="Bit Toggle Controls")
        self.bit_toggle_frame.pack(pady=10)

        # Create Bit Toggle Buttons
        self.bit_toggle_buttons = [[None for _ in range(8)] for _ in range(8)]
        for byte_index in range(8):
            for bit_index in range(8):
                btn = ttk.Button(self.bit_toggle_frame, text=f"Byte {byte_index} Bit {bit_index}", width=12,
                                 command=lambda b=byte_index, bi=bit_index: self.toggle_bit(b, bi))
                btn.grid(row=byte_index, column=bit_index, padx=2, pady=2)
                self.bit_toggle_buttons[byte_index][bit_index] = btn

    def toggle_bruteforce(self):
        if not self.running:
            self.running = True
            self.start_button.config(text="Stop Brute-Force")
            self.status_label.config(text="Status: Running")
            self.output_text.insert(tk.END, "Brute-force started...\n")
            self.start_bruteforce()
        else:
            self.running = False
            self.start_button.config(text="Start Brute-Force")
            self.status_label.config(text="Status: Stopped")
            self.output_text.insert(tk.END, "Brute-force stopped.\n")

    def start_bruteforce(self):
        # Start brute-forcing in a separate thread
        self.bruteforce_thread = threading.Thread(target=self.bruteforce_loop)
        self.bruteforce_thread.daemon = True
        self.bruteforce_thread.start()

    def bruteforce_loop(self):
        while self.running:
            current_time = time.time()

            # Check if it's time to send a message every 100ms
            if current_time - self.last_send_time >= 0.1:
                self.send_can_message()
                self.last_send_time = current_time

            # Check if it's time to change the bit position every 3 seconds and auto increment is enabled
            if self.auto_increment.get() and current_time - self.last_bit_change_time >= 3:
                self.update_bit_position()
                self.last_bit_change_time = current_time

            time.sleep(0.01)  # Small sleep to prevent high CPU usage

    def send_can_message(self):
        # Create a message with the current bit states
        data = [0] * 8
        for byte_index in range(8):
            for bit_index in range(8):
                if self.bit_states[byte_index][bit_index] == 1:
                    data[byte_index] |= (1 << bit_index)
                else:
                    data[byte_index] &= ~(1 << bit_index)

        # Create a CAN message
        message = can.Message(arbitration_id=self.current_id, data=data, is_extended_id=False)

        try:
            bus.send(message)
            self.output_text.insert(tk.END, f"Sent: ID={hex(self.current_id)} Data={data}\n")
            self.output_text.see(tk.END)
        except can.CanError as e:
            self.output_text.insert(tk.END, f"CAN Error: {str(e)}\n")

    def toggle_bit(self, byte_index, bit_index):
        # Toggle the state of the specified bit
        self.bit_states[byte_index][bit_index] ^= 1  # Flip the bit (0 -> 1, 1 -> 0)
        self.output_text.insert(tk.END, f"Toggled Byte {byte_index} Bit {bit_index} to {self.bit_states[byte_index][bit_index]}\n")

    def update_bit_position(self):
        # Move to the next bit position
        self.current_bit_position += 1

        if self.current_bit_position > 7:
            self.current_bit_position = 0
            self.current_byte_index += 1

        if self.current_byte_index > 7:
            self.current_byte_index = 0
            self.current_id += 1

        # Reset ID if it reaches the end
        if self.current_id > 0x7FF:
            self.current_id = 0

    def apply_id(self):
        # Update the CAN ID from user input
        try:
            new_id = int(self.id_entry.get(), 16)
            if 0 <= new_id <= 0x7FF:
                self.current_id = new_id
                self.output_text.insert(tk.END, f"CAN ID set to: {hex(self.current_id)}\n")
            else:
                self.output_text.insert(tk.END, "Error: ID must be between 0x000 and 0x7FF.\n")
        except ValueError:
            self.output_text.insert(tk.END, "Error: Invalid ID format.\n")

    def increment_bit(self):
        # Manually increment the bit position
        self.current_bit_position += 1
        if self.current_bit_position > 7:
            self.current_bit_position = 0
            self.current_byte_index += 1
        if self.current_byte_index > 7:
            self.current_byte_index = 0
        self.output_text.insert(tk.END, f"Bit position manually incremented to byte {self.current_byte_index}, bit {self.current_bit_position}\n")

    def decrement_bit(self):
        # Manually decrement the bit position
        self.current_bit_position -= 1
        if self.current_bit_position < 0:
            self.current_bit_position = 7
            self.current_byte_index -= 1
        if self.current_byte_index < 0:
            self.current_byte_index = 7
        self.output_text.insert(tk.END, f"Bit position manually decremented to byte {self.current_byte_index}, bit {self.current_bit_position}\n")

if __name__ == "__main__":
    app = CanBruteForcer()
    app.mainloop()
