# scanner.py
import os
import subprocess
import json
import re

def get_system_printers():
    """Get list of printers installed in the system"""
    devices = []
    
    try:
        if os.name == 'posix':  # macOS or Linux
            if 'darwin' in os.sys.platform:  # macOS
                # Use lpstat to get printer list on macOS
                result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if line.startswith("printer "):
                            # Extract printer name
                            printer_name = line.split()[1]
                            
                            # Check if it's a Brother printer (optional)
                            is_brother = False
                            try:
                                info_result = subprocess.run(["lpoptions", "-p", printer_name, "-l"], 
                                                          capture_output=True, text=True)
                                if "brother" in info_result.stdout.lower() or "ql" in info_result.stdout.lower():
                                    is_brother = True
                            except:
                                pass
                            
                            devices.append({
                                'name': f"System Printer: {printer_name}" + (" (Brother)" if is_brother else ""),
                                'address': printer_name,  # Use printer name as the address
                                'type': 'system'
                            })
            else:  # Linux
                # Use lpstat for Linux as well
                result = subprocess.run(["lpstat", "-a"], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if " accepting requests" in line:
                            printer_name = line.split()[0]
                            devices.append({
                                'name': f"System Printer: {printer_name}",
                                'address': printer_name,
                                'type': 'system'
                            })
                
                # If no printers found with lpstat, try CUPS method
                if not devices:
                    try:
                        result = subprocess.run(["lpinfo", "-v"], capture_output=True, text=True)
                        if result.returncode == 0:
                            for line in result.stdout.splitlines():
                                if "://" in line:  # It's a printer URI
                                    parts = line.split(" ", 1)
                                    if len(parts) > 1:
                                        uri = parts[1]
                                        name = uri.split("/")[-1]
                                        devices.append({
                                            'name': f"System Printer: {name}",
                                            'address': name,
                                            'type': 'system'
                                        })
                    except:
                        pass
        else:  # Windows
            # For Windows, we would use wmic
            try:
                result = subprocess.run(
                    ["wmic", "printer", "get", "name"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines()[1:]:  # Skip header
                        printer_name = line.strip()
                        if printer_name:  # Skip empty lines
                            devices.append({
                                'name': f"System Printer: {printer_name}",
                                'address': printer_name,
                                'type': 'system'
                            })
            except:
                # Try PowerShell if wmic fails
                try:
                    result = subprocess.run(
                        ["powershell", "-Command", "Get-Printer | Format-Table Name"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.splitlines()[3:]:  # Skip header
                            printer_name = line.strip()
                            if printer_name and not printer_name.startswith("-"):  # Skip separator lines
                                devices.append({
                                    'name': f"System Printer: {printer_name}",
                                    'address': printer_name,
                                    'type': 'system'
                                })
                except:
                    pass
    except Exception as e:
        print(f"Error getting system printers: {e}")
    
    return devices