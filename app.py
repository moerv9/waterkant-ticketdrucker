from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import importlib
import time
from threading import Thread
from PIL import Image, ImageDraw, ImageFont
import re

# Import our printer management modules
from printer_manager.scanner import get_system_printers
from printer_manager.connection import test_printer_connection, update_print_module
import printer_manager.print_module as print_module

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Create necessary directories
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)
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

# Route for serving the main HTML page
@app.route('/')
def index():
    return render_template('index.html')

# Import the original create_image_with_name function and modify print_name to use our dynamic module
@app.route('/print-name', methods=['POST'])
def handle_print_name():
    try:
        # Check for Name in Request Body
        data = request.get_json()
        if 'attendee_firstname' not in data or 'attendee_lastname' not in data:
            # return error if the first and last name is missing
            return jsonify({"error": "Missing first or last name in request body"}), 400
        
        # Check if printer is connected
        if not printer_state["connected"]:
            return jsonify({"error": "No printer connected. Please connect a system printer first."}), 400
            
        first_name = data['attendee_firstname']
        last_name = data['attendee_lastname']
        
        # Reload the print module to get any updates
        importlib.reload(print_module)
        
        # Create the image - use landscape orientation for the label printer
        # Brother QL printers typically use 62mm width labels
        # For 62mm label, we'll use a width of 696 pixels (at 300dpi)
        # Height will depend on the label length, but 271 is typical for a name tag
        
        # For Brother QL printers, the "width" is actually the height in portrait orientation
        # and "height" is the width when we print in landscape. It's confusing but that's how it works.
        height = 696  # This is actually the width when we print in landscape
        width = 271   # This is actually the height when we print in landscape
        
        image = Image.new("RGB", (width, height), "white")
        
        # Initialize the drawing context
        draw = ImageDraw.Draw(image)
        
        font_size = 128
        
        # Adjust font size based on name length
        if(len(first_name) >= 8 or len(last_name) >= 8):
            longest_name = first_name if(len(first_name) > len(last_name)) else last_name 
            oversize = len(longest_name) - 8
            font_size = 128 - 12.32381 * oversize + 0.552381 * oversize ** 2
            print(f"Adjusted font size to {font_size} due to name length")
        
        # Check for the font, use default if not available
        try:
            font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=int(font_size))
        except:
            # Use default font if the specified one is not available
            try:
                # Try to find a system font
                default_font = None
                if os.path.exists('/Library/Fonts/Arial.ttf'):  # macOS
                    default_font = '/Library/Fonts/Arial.ttf'
                elif os.path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):  # Linux
                    default_font = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
                elif os.path.exists('C:\\Windows\\Fonts\\Arial.ttf'):  # Windows
                    default_font = 'C:\\Windows\\Fonts\\Arial.ttf'
                
                if default_font:
                    font = ImageFont.truetype(font=default_font, size=int(font_size))
                else:
                    # If no system font found, use default PIL font
                    font = ImageFont.load_default()
            except:
                # Fallback to default PIL font
                font = ImageFont.load_default()
        
        # We'll rotate the text 90 degrees to match the landscape orientation
        # This approach creates the text in the correct rotation for the label printer
        # First, create a text-only image for first name
        first_bbox = draw.textbbox((0, 0), first_name, font=font)
        first_width = first_bbox[2] - first_bbox[0]
        first_height = first_bbox[3] - first_bbox[1]
        
        # Center text horizontally
        # For landscape orientation, we're centering along the long edge of the label (height)
        first_x = (height - first_width) / 2
        
        # Position first name in the top third of the image
        first_y = width / 4 - first_height / 2
        
        # Same for last name
        last_bbox = draw.textbbox((0, 0), last_name, font=font)
        last_width = last_bbox[2] - last_bbox[0]
        last_height = last_bbox[3] - last_bbox[1]
        
        last_x = (height - last_width) / 2
        last_y = 3 * width / 4 - last_height / 2
        
        # Rotate the image 90 degrees for landscape orientation
        # We need to transpose the coordinates for the rotated image
        # In a landscape-rotated image, (0,0) is at the top-right corner
        
        # Draw the text on the image
        # For a rotated image in PILLOW:
        # - first_x becomes y value counting from top
        # - first_y becomes x value counting from right to left
        
        # Rotate the entire canvas 90 degrees counter-clockwise
        rotated_image = image.rotate(90, expand=True)
        rotated_draw = ImageDraw.Draw(rotated_image)
        
        # Now draw the text in the rotated canvas
        rotated_draw.text((first_y, first_x), first_name, fill="black", font=font)
        rotated_draw.text((last_y, last_x), last_name, fill="black", font=font)
        
        # Create path without whitespaces
        os.makedirs("./img", exist_ok=True)
        path = re.sub(r'\s+', '', f"./img/{first_name}{last_name}.png")
        
        # Save the rotated image
        rotated_image.save(path)
        
        # Print using our dynamically loaded module
        print_success = print_module.print_name(path)
        
        if print_success:
            return jsonify({"message": "Print successful", "data": {"first_name": first_name, "last_name": last_name}}), 200
        else:
            return jsonify({"message": "Print failed, but image saved", "data": {"first_name": first_name, "last_name": last_name, "image_path": path}}), 202
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5555, debug=True)