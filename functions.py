from PIL import Image, ImageDraw, ImageFont
import re
import subprocess
import os
import json

# Create necessary directories
os.makedirs("img", exist_ok=True)
printer_state_file = "printer_state.json"

def load_printer_state():
    """Load printer state from file or return default state"""
    default_state = {
        "connected": False,
        "method": None,
        "address": None,
        "model": "QL-820NWB",
        "status": "Not connected",
        "last_attempt": None
    }
    
    try:
        if os.path.exists(printer_state_file):
            with open(printer_state_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading printer state: {e}")
    
    return default_state

def create_dynamic_label(first_name, last_name, layout="side_by_side", font_size=100, padding=10):
    """
    Create a label image with dynamic dimensions based on font size.
    
    Args:
        first_name (str): First name
        last_name (str): Last name
        layout (str): Either "side_by_side" or "stacked"
        font_size (int): Font size to use
        padding (int): Padding around the text in pixels
        
    Returns:
        str: Path to the created image
        tuple: (width, height) of the created image
    """
    # Load the font for measurements
    font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=font_size)
    
    # Create a temporary drawing context for measurements
    temp_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(temp_img)
    
    # Calculate dimensions based on layout
    if layout == "side_by_side":
        # Put first and last name side by side
        text = f"{first_name} {last_name}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate image dimensions with padding
        width = text_width + (2 * padding)
        height = text_height + (2 * padding)
        
        # Create the actual image with calculated dimensions
        image = Image.new("RGB", (width, height), "white")
        final_draw = ImageDraw.Draw(image)
        
        # Draw the text centered
        x = padding
        y = padding
        final_draw.text((x, y), text, fill="black", font=font)
        
    else:  # stacked layout
        # Calculate dimensions for each name
        first_bbox = draw.textbbox((0, 0), first_name, font=font)
        last_bbox = draw.textbbox((0, 0), last_name, font=font)
        
        first_width = first_bbox[2] - first_bbox[0]
        first_height = first_bbox[3] - first_bbox[1]
        
        last_width = last_bbox[2] - last_bbox[0]
        last_height = last_bbox[3] - last_bbox[1]
        
        # Calculate the maximum width needed
        max_width = max(first_width, last_width)
        
        # Calculate total height with spacing between names
        vertical_spacing = font_size // 10  # Proportional spacing
        total_height = first_height + vertical_spacing + last_height
        
        # Calculate image dimensions with padding
        width = max_width + (2 * padding)
        height = total_height + (2 * padding)
        
        # Create the actual image with calculated dimensions
        image = Image.new("RGB", (width, height), "white")
        final_draw = ImageDraw.Draw(image)
        
        # Calculate positions for centered text
        first_x = padding + (max_width - first_width) // 2
        last_x = padding + (max_width - last_width) // 2
        
        # Draw the text
        first_y = padding
        last_y = padding + first_height + vertical_spacing
        
        final_draw.text((first_x, first_y), first_name, fill="black", font=font)
        final_draw.text((last_x, last_y), last_name, fill="black", font=font)
    
    # Create a file path
    path = re.sub(r'\s+', '', f"./img/{first_name}{last_name}.png")
    
    # Save the image
    image.save(path)
    print(f"Created dynamic label at {path} with dimensions {width}x{height}")
    
    return path, (width, height)

def create_simple_label(first_name, last_name, layout="side_by_side", 
                     font_size=300, width=731, height=300):
    """
    Create a label with fixed dimensions and font size.
    
    Args:
        first_name (str): First name
        last_name (str): Last name
        layout (str): Either "side_by_side" or "stacked"
        font_size (int): Font size to use (exact size, no auto-scaling)
        width (int): Label width in pixels
        height (int): Label height in pixels
        
    Returns:
        str: Path to the created image
    """
    # Create white background image with specified dimensions
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    
    # Load font with exact specified size
    font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=font_size)
    
    if layout == "side_by_side":
        # Side by side layout - both names on same line
        text = f"{first_name} {last_name}"
        
        # Get text dimensions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center text both horizontally and vertically
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw the text
        draw.text((x, y), text, fill="black", font=font)
        
    else:  # stacked layout
        # Calculate slightly smaller font for last name
        first_font = font
        last_font = ImageFont.truetype(font='./font/Dia-Black.ttf', size=int(font_size * 0.8))
        
        # Get text dimensions
        first_bbox = draw.textbbox((0, 0), first_name, font=first_font)
        last_bbox = draw.textbbox((0, 0), last_name, font=last_font)
        
        first_width = first_bbox[2] - first_bbox[0]
        first_height = first_bbox[3] - first_bbox[1]
        
        last_width = last_bbox[2] - last_bbox[0]
        last_height = last_bbox[3] - last_bbox[1]
        
        # Calculate vertical spacing between names
        spacing = font_size // 10
        
        # Calculate total content height
        total_height = first_height + spacing + last_height
        
        # Center content vertically
        start_y = (height - total_height) // 2
        
        # Center each name horizontally
        first_x = (width - first_width) // 2
        last_x = (width - last_width) // 2
        
        # Draw the text
        draw.text((first_x, start_y), first_name, fill="black", font=first_font)
        draw.text((last_x, start_y + first_height + spacing), last_name, fill="black", font=last_font)
    
    # Create a file path
    path = re.sub(r'\s+', '', f"./img/{first_name}{last_name}.png")
    
    # Save the image
    image.save(path)
    print(f"Created label at {path} with dimensions {width}x{height}, font size {font_size}")
    
    return path

def print_name(path, printer_address=None):
    """
    Print an image using the system printer.
    
    Args:
        path (str): Path to the image file to print
        printer_address (str, optional): Printer address to use.
            If None, will use the address from the stored printer state.
    
    Returns:
        bool: True if print was successful, False otherwise
    """
    try:
        # If no printer_address provided, get it from the saved state
        if printer_address is None:
            printer_state = load_printer_state()
            printer_address = printer_state.get("address")
            
            if not printer_address or not printer_state.get("connected", False):
                print(f"No printer connected. Image saved at: {path}")
                return False
        
        print(f"Printing image {path} to printer {printer_address}")
        
        # Simple printing command
        cmd = ["lp", "-d", printer_address, path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("Print successful.")
            return True
        else:
            print(f"Print failed: {result.stderr}")
            # Try alternative options if the basic command fails
            alternative_cmds = [
                ["lp", "-d", printer_address, "-o", "raw", path],  # Try with raw option
                ["lp", "-d", printer_address, "-o", "media=Custom.62x100mm", path]  # Try with media size
            ]
            
            for alt_cmd in alternative_cmds:
                print(f"Trying alternative command: {' '.join(alt_cmd)}")
                alt_result = subprocess.run(alt_cmd, capture_output=True, text=True, timeout=10)
                if alt_result.returncode == 0:
                    print("Print successful with alternative options.")
                    return True
            
            return False
    except Exception as e:
        print(f"Exception during printing: {e}")
        return False