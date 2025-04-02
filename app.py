from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import importlib
import time
from threading import Thread
from PIL import Image, ImageDraw, ImageFont
import re
import subprocess
# Import our printer management modules
from printer_manager.scanner import get_system_printers
from printer_manager.connection import test_printer_connection, update_print_module
import printer_manager.print_module as print_module

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Create necessary directories
os.makedirs("img", exist_ok=True)

# Global printer connection state - persistent across app restarts
printer_state_file = "printer_state.json"

# Default printer state
default_printer_state = {
    "connected": False,
    "method": None,
    "address": None,
    "model": "QL-820NWB",
    "status": "Not connected",
    "last_attempt": None
}
PRINTER_ADDRESS = "Brother_QL_820NWB__94ddf8a529c6_"
# Load printer state from file or use default
def load_printer_state():
    try:
        if os.path.exists(printer_state_file):
            with open(printer_state_file, 'r') as f:
                import json
                state = json.load(f)
                
                # Verify the connection is still valid
                if state.get("connected", False) and state.get("address"):
                    if test_printer_connection(state.get("method", "system"), state.get("address"), state.get("model", "QL-820NWB")):
                        # If connection is still valid, update print_module
                        update_print_module(state)
                        return state
                    else:
                        # Connection is no longer valid
                        state["connected"] = False
                        state["status"] = "Printer disconnected"
                        save_printer_state(state)
                        return state
                return state
    except Exception as e:
        print(f"Error loading printer state: {e}")
    return default_printer_state.copy()

# Save printer state to file
def save_printer_state(state):
    try:
        with open(printer_state_file, 'w') as f:
            import json
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving printer state: {e}")

# Initialize global printer state
printer_state = load_printer_state()

# API routes for printer connection management
@app.route('/api/printer/status', methods=['GET'])
def get_printer_status():
    global printer_state
    
    # Verify connection is still valid
    if printer_state.get("connected", False) and printer_state.get("address"):
        if not test_printer_connection(printer_state.get("method", "system"), 
                                     printer_state.get("address"), 
                                     printer_state.get("model", "QL-820NWB")):
            # Connection is no longer valid
            printer_state["connected"] = False
            printer_state["status"] = "Printer disconnected"
            save_printer_state(printer_state)
    
    return jsonify(printer_state)

@app.route('/api/printer/scan/system', methods=['POST'])
def handle_scan_system():
    """Get all printers installed in the system"""
    devices = get_system_printers()
    return jsonify({"devices": devices})

@app.route('/api/printer/connect', methods=['POST'])
def handle_connect():
    global printer_state
    
    data = request.get_json()
    
    if 'address' not in data or 'method' not in data:
        return jsonify({"error": "Missing address or method"}), 400
    
    method = data['method']
    address = data['address']
    
    printer_state["status"] = f"Connecting to {method} printer at {address}..."
    
    if test_printer_connection(method, address, printer_state["model"]):
        printer_state["connected"] = True
        printer_state["method"] = method
        printer_state["address"] = address
        printer_state["status"] = f"Connected via {method.upper()}"
        printer_state["last_attempt"] = time.time()
        
        # Update the print module with the new connection
        update_print_module(printer_state)
        
        # Save the state
        save_printer_state(printer_state)
    else:
        printer_state["connected"] = False
        printer_state["status"] = f"Failed to connect to {method} printer at {address}"
        printer_state["last_attempt"] = time.time()
        save_printer_state(printer_state)
    
    return jsonify(printer_state)

def print_label(path):
    """Function to print an image using brother_ql."""
    try:
        print(f"Printing image {path} with brother_ql")
        # Use brother_ql with proper settings
        os.system(f"brother_ql print -l 62 --dpi 300 --rotate 0 {path}")
        print("Print command executed.")
        
        # Optional: only remove the file if successful printing is confirmed
        os.remove(path)
        return True
    except Exception as e:
        print(f"Exception during printing: {e}")
        return False


# --- Static print function ---
def print_name(path):
    """Static function to print an image using the system printer."""
    try:
        print(f"Printing image {path} to printer {PRINTER_ADDRESS}")
        # Simple printing command (you can adjust options as needed)
        cmd = ["lp", "-d", PRINTER_ADDRESS, path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("Print successful.")
            return True
        else:
            print(f"Print failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Exception during printing: {e}")
        return False

# --- Simplified image creation function ---
def create_image_with_name(first_name, last_name, width=696, height=271):
    # Create a white background image
    image = Image.new("RGB", (width, height), "white")
    
    # Initialize the drawing context
    draw = ImageDraw.Draw(image)
    
    font_size = 128

    if len(first_name) >= 8 or len(last_name) >= 8:
        longest_name = first_name if len(first_name) > len(last_name) else last_name
        oversize = len(longest_name) - 8
        font_size = 128 - 12.32381 * oversize + 0.552381 * oversize ** 2
        print(f"Adjusted font size to: {font_size}")

    # Load the font – adjust the font path if necessary
    font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=int(font_size))
    
    # Center the text (here we simply use the whole image dimensions)
    text_width, text_height = width, height
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2
    
    # Draw first name on the top half and last name on the bottom half
    draw.text((text_x, 0), first_name, fill="black", font=font)
    draw.text((text_x, text_height / 2), last_name, fill="black", font=font)
    
    # Create a file path (remove whitespace)
    path = re.sub(r'\s+', '', f"./img/{first_name}{last_name}.png")
    
    # Save the image
    image.save(path)
    
    # Print the image using our static print function
    print_name(path)
    
    return path

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route ("/test")
def test():
    return render_template('test.html')

@app.route('/print-name', methods=['POST'])
def handle_print_name():
    try:
        data = request.get_json()
        if 'attendee_firstname' not in data or 'attendee_lastname' not in data:
            return jsonify({"error": "Missing first or last name in request body"}), 400

        first_name = data['attendee_firstname']
        last_name = data['attendee_lastname']

        # Create the image with the name (this also calls print_name)
        image_path = create_image_with_name(first_name, last_name)
        
        return jsonify({
            "message": "Print initiated",
            "data": {
                "first_name": first_name,
                "last_name": last_name,
                "image_path": image_path
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5555, debug=True)