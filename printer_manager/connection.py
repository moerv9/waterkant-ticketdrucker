import subprocess
import os
import re

def test_printer_connection(method, address, model):
    """Test if we can connect to the printer"""
    if method == "system":
        # For system printers, check if the printer exists in the system
        try:
            print(f"Testing connection to system printer: {address}")
            
            if os.name == 'posix':  # macOS or Linux
                result = subprocess.run(["lpstat", "-p", address], 
                                      capture_output=True, text=True, timeout=5)
                connected = result.returncode == 0
                print(f"lpstat connection test result: {connected}")
                return connected
            else:  # Windows
                # For Windows, use wmic to check printer existence
                result = subprocess.run(
                    ["wmic", "printer", "where", f"name='{address}'", "get", "name"],
                    capture_output=True, text=True, timeout=5
                )
                connected = address in result.stdout
                print(f"wmic connection test result: {connected}")
                return connected
        except Exception as e:
            # Try an alternative check if the first method fails
            print(f"Primary connection test failed: {e}")
            try:
                if os.name == 'posix':  # macOS or Linux
                    # Try a simple lp command with -o printer-info
                    result = subprocess.run(["lp", "-d", address, "-o", "printer-info"],
                                          capture_output=True, text=True, timeout=5)
                    connected = "no such printer" not in result.stderr.lower()
                    print(f"Alternative connection test result: {connected}")
                    return connected
                else:  # Windows - Try PowerShell
                    result = subprocess.run(
                        ["powershell", "-Command", f"Get-Printer -Name '{address}'"],
                        capture_output=True, text=True, timeout=5
                    )
                    connected = result.returncode == 0
                    print(f"PowerShell connection test result: {connected}")
                    return connected
            except Exception as e2:
                print(f"Alternative connection test failed: {e2}")
                return False
    
    print("No valid connection method specified")
    return False

def create_print_function(printer_config):
    """Generate the appropriate print_name function based on connection method"""
    if printer_config["method"] == "system":
        return f"""
def print_name(path):
    # Use system printing capabilities for a printer installed on the system
    try:
        print(f"Printing to system printer '{printer_config['address']}' with image: {{path}}")
        
        # Try several different printing options
        # Note: Different Brother QL printers might need different options
        
        # Option 1: Simple printing with no special options
        cmd = ["lp", "-d", "{printer_config['address']}", path]
        
        print(f"Trying command: {{' '.join(cmd)}}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"Print successful: {{result.stdout}}")
            return True
        else:
            print(f"Basic print failed: {{result.stderr}}")
            print(f"Trying alternative options...")
            
            # Option 2: Try with raw output
            cmd = ["lp", "-d", "{printer_config['address']}", "-o", "raw", path]
            print(f"Trying command: {{' '.join(cmd)}}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"Print with raw option successful: {{result.stdout}}")
                return True
            else:
                print(f"Print with raw option failed: {{result.stderr}}")
                
                # Option 3: Try with specific media type for label printers
                cmd = ["lp", "-d", "{printer_config['address']}", 
                       "-o", "media=Custom.62x100mm", path]
                print(f"Trying command: {{' '.join(cmd)}}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"Print with custom media successful: {{result.stdout}}")
                    return True
                else:
                    print(f"All print options failed. Last error: {{result.stderr}}")
                    return False
    except Exception as e:
        print(f"Exception during printing: {{e}}")
        print(f"Image saved at: {{path}}")
        return False
"""
    else:
        # Default to a function that just saves the file
        return """
def print_name(path):
    print(f"No printer connected. Image saved at: {path}")
    return False
"""

def update_print_module(printer_config):
    """Update the print_module.py file with the correct printing function"""
    # Ensure the printer_manager directory exists
    os.makedirs("printer_manager", exist_ok=True)
    
    print(f"Updating print_module.py with printer: {printer_config.get('address', 'None')}")
    
    with open("printer_manager/print_module.py", "w") as f:
        f.write("""
# Dynamically generated printing module
import os
import subprocess

""" + create_print_function(printer_config))
    
    print(f"print_module.py updated successfully")

    # Create init file if it doesn't exist
    init_path = "printer_manager/__init__.py"
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("# Printer manager package\n")