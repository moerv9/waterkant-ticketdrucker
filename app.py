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
from printer_manager.connection import test_printer_connection

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
        
        # Save the state
        save_printer_state(printer_state)
    else:
        printer_state["connected"] = False
        printer_state["status"] = f"Failed to connect to {method} printer at {address}"
        printer_state["last_attempt"] = time.time()
        save_printer_state(printer_state)
    
    return jsonify(printer_state)


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
    
def create_image_with_name(first_name, last_name, width=696, height=271, 
                          first_font_size=None, last_font_size=None, 
                          vertical_spacing=10):
    """
    Create an image with first and last name, with improved positioning and sizing.
    
    Args:
        first_name (str): First name to print
        last_name (str): Last name to print
        width (int): Image width in pixels
        height (int): Image height in pixels
        first_font_size (int): Optional custom font size for first name
        last_font_size (int): Optional custom font size for last name
        vertical_spacing (int): Space between first and last name
        
    Returns:
        str: Path to the created image
    """
    # Create a white background image
    image = Image.new("RGB", (width, height), "white")
    
    # Initialize the drawing context
    draw = ImageDraw.Draw(image)
    
    # Calculate font sizes if not provided
    if first_font_size is None:
        # Default font size with scaling for long names
        first_font_size = 128
        if len(first_name) >= 8:
            oversize = len(first_name) - 8
            first_font_size = 128 - 12 * oversize + 0.5 * oversize ** 2
    
    if last_font_size is None:
        # Default font size with scaling for long names
        last_font_size = 128
        if len(last_name) >= 8:
            oversize = len(last_name) - 8
            last_font_size = 128 - 12 * oversize + 0.5 * oversize ** 2
    
    # Load fonts
    first_font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=int(first_font_size))
    last_font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=int(last_font_size))
    
    # Get actual text dimensions
    first_bbox = draw.textbbox((0, 0), first_name, font=first_font)
    last_bbox = draw.textbbox((0, 0), last_name, font=last_font)
    
    first_text_width = first_bbox[2] - first_bbox[0]
    first_text_height = first_bbox[3] - first_bbox[1]
    
    last_text_width = last_bbox[2] - last_bbox[0]
    last_text_height = last_bbox[3] - last_bbox[1]
    
    # Calculate total content height
    total_content_height = first_text_height + vertical_spacing + last_text_height
    
    # Center text horizontally and vertically
    first_x = (width - first_text_width) / 2
    last_x = (width - last_text_width) / 2
    
    # If content fits, center vertically
    y_start = (height - total_content_height) / 2
    
    # Draw the text
    draw.text((first_x, y_start), first_name, fill="black", font=first_font)
    draw.text((last_x, y_start + first_text_height + vertical_spacing), 
              last_name, fill="black", font=last_font)
    
    # Create a file path (remove whitespace)
    path = re.sub(r'\s+', '', f"./img/{first_name}{last_name}.png")
    
    # Save the image
    image.save(path)
    print(f"Created image at {path} with dimensions {width}x{height}")
    
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
        
        # Required parameters
        if 'attendee_firstname' not in data or 'attendee_lastname' not in data:
            return jsonify({"error": "Missing first or last name in request body"}), 400

        first_name = data['attendee_firstname']
        last_name = data['attendee_lastname']
        
        # Optional parameters with defaults
        width = data.get('width', 696)  
        height = data.get('height', 271)
        first_font_size = data.get('first_font_size')
        last_font_size = data.get('last_font_size')
        vertical_spacing = data.get('vertical_spacing', 10)
        
        # Print debug info
        print(f"Creating name tag for: {first_name} {last_name}")
        print(f"Dimensions: {width}x{height}")
        print(f"Font sizes: first={first_font_size}, last={last_font_size}")
        
        # Create the image with the name
        image_path = create_image_with_name(
            first_name, 
            last_name,
            width=width,
            height=height,
            first_font_size=first_font_size,
            last_font_size=last_font_size,
            vertical_spacing=vertical_spacing
        )
        
        # Print the image
        print_success = print_name(image_path)
        
        return jsonify({
            "message": "Print initiated",
            "success": print_success,
            "data": {
                "first_name": first_name,
                "last_name": last_name,
                "image_path": image_path,
                "width": width,
                "height": height,
                "first_font_size": first_font_size,
                "last_font_size": last_font_size
            }
        }), 200

    except Exception as e:
        print(f"Error in print-name endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

def create_label(first_name, last_name, layout="side_by_side", 
                max_font_size=100, width=731, height=118):
    """
    Create a label image optimized for a small 62mm x 10mm label.
    
    Args:
        first_name (str): First name
        last_name (str): Last name
        layout (str): Either "side_by_side" or "stacked"
        max_font_size (int): Maximum font size to attempt
        width (int): Image width in pixels (default 731px = 62mm at 300dpi)
        height (int): Image height in pixels (default 118px = 10mm at 300dpi)
        
    Returns:
        str: Path to the created image
    """
    # Create a white background image
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    
    if layout == "side_by_side":
        # Put first and last name side by side
        text = f"{first_name} {last_name}"
        
        # Find the largest font size that fits the width
        font_size = max_font_size
        font = None
        text_width = width + 1  # Initialize larger than width to enter loop
        
        while text_width > width - 20 and font_size > 10:
            font_size -= 5
            font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=font_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        
        # Center the text
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw the text
        draw.text((x, y), text, fill="black", font=font)
        
    else:  # stacked layout
        # Calculate font sizes - use larger font for first name
        first_size = max_font_size
        last_size = int(max_font_size * 0.8)  # Last name slightly smaller
        
        # Find font sizes that fit
        while True:
            first_font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=first_size)
            last_font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=last_size)
            
            first_bbox = draw.textbbox((0, 0), first_name, font=first_font)
            last_bbox = draw.textbbox((0, 0), last_name, font=last_font)
            
            first_width = first_bbox[2] - first_bbox[0]
            first_height = first_bbox[3] - first_bbox[1]
            
            last_width = last_bbox[2] - last_bbox[0]
            last_height = last_bbox[3] - last_bbox[1]
            
            # Check if it fits within width and height (with 5px spacing)
            total_height = first_height + last_height + 5
            
            if (first_width <= width - 20 and last_width <= width - 20 and 
                total_height <= height - 10):
                break
                
            # Reduce font size and try again
            first_size -= 5
            last_size = int(first_size * 0.8)
            
            # Prevent infinite loop with tiny fonts
            if first_size < 10:
                first_size = 10
                last_size = 8
                break
        
        # Calculate positions (center horizontally)
        first_x = (width - first_width) // 2
        last_x = (width - last_width) // 2
        
        # Calculate vertical positioning
        y_start = (height - total_height) // 2
        
        # Draw text
        draw.text((first_x, y_start), first_name, fill="black", font=first_font)
        draw.text((last_x, y_start + first_height + 5), last_name, fill="black", font=last_font)
    
    # Create a file path
    path = re.sub(r'\s+', '', f"./img/{first_name}{last_name}.png")
    
    # Save the image
    image.save(path)
    print(f"Created label at {path} with dimensions {width}x{height}")
    
    return path

@app.route('/print-label', methods=['POST'])
def handle_print_label():
    try:
        data = request.get_json()
        
        # Required parameters
        if 'first_name' not in data or 'last_name' not in data:
            return jsonify({"error": "Missing first or last name in request body"}), 400

        first_name = data['first_name']
        last_name = data['last_name']
        
        # Optional parameters with defaults
        layout = data.get('layout', 'side_by_side')  # 'side_by_side' or 'stacked'
        max_font_size = data.get('max_font_size', 100)
        width = data.get('width', 731)  # 62mm at 300dpi
        height = data.get('height', 118)  # 10mm at 300dpi
        
        # Print debug info
        print(f"Creating label for: {first_name} {last_name}")
        print(f"Layout: {layout}, Max font size: {max_font_size}")
        print(f"Dimensions: {width}x{height}")
        
        # Create the label
        image_path = create_label(
            first_name, 
            last_name,
            layout=layout,
            max_font_size=max_font_size,
            width=width,
            height=height
        )
        
        # Print the image
        print_success = print_name(image_path)
        
        return jsonify({
            "message": "Print initiated",
            "success": print_success,
            "data": {
                "first_name": first_name,
                "last_name": last_name,
                "image_path": image_path,
                "layout": layout,
                "max_font_size": max_font_size,
                "width": width,
                "height": height
            }
        }), 200

    except Exception as e:
        print(f"Error in print-label endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5555, debug=True)