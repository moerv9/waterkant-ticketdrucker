from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import time
from functions import (
    create_dynamic_label,
    create_simple_label,
    print_name,
    load_printer_state,
)
from printer_manager.scanner import get_system_printers
from printer_manager.connection import test_printer_connection


# Initialize Flask
app = Flask(__name__)
CORS(app)

# Global printer connection state - persistent across app restarts
printer_state_file = "printer_state.json"

# Default printer state
default_printer_state = {
    "connected": False,
    "method": None,
    "address": None,
    "model": "QL-820NWB",
    "status": "Not connected",
    "last_attempt": None,
}


# Save printer state to file
def save_printer_state(state):
    try:
        with open(printer_state_file, "w") as f:
            import json

            json.dump(state, f)
    except Exception as e:
        print(f"Error saving printer state: {e}")


# Initialize global printer state
printer_state = load_printer_state()


# API routes for printer connection management
@app.route("/api/printer/status", methods=["GET"])
def get_printer_status():
    global printer_state

    # Verify connection is still valid
    if printer_state.get("connected", False) and printer_state.get("address"):
        if not test_printer_connection(
            printer_state.get("method", "system"),
            printer_state.get("address"),
            printer_state.get("model", "QL-820NWB"),
        ):
            # Connection is no longer valid
            printer_state["connected"] = False
            printer_state["status"] = "Printer disconnected"
            save_printer_state(printer_state)

    return jsonify(printer_state)


@app.route("/api/printer/scan/system", methods=["POST"])
def handle_scan_system():
    """Get all printers installed in the system"""
    devices = get_system_printers()
    return jsonify({"devices": devices})


@app.route("/api/printer/connect", methods=["POST"])
def handle_connect():
    global printer_state

    data = request.get_json()

    if "address" not in data or "method" not in data:
        return jsonify({"error": "Missing address or method"}), 400

    method = data["method"]
    address = data["address"]

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


# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/test")
def test():
    return render_template("test.html")


@app.route("/dynamic-test")
def dynamic_test():
    return render_template("dynamic_test.html")


@app.route("/fixed-width-test")
def fixed_width_test():
    return render_template("fixed_width_test.html")


@app.route("/print-dynamic", methods=["POST"])
def handle_print_dynamic():
    try:
        global printer_state
        data = request.get_json()

        # Required parameters
        if "first_name" not in data or "last_name" not in data:
            return jsonify({"error": "Missing first or last name in request body"}), 400

        first_name = data["first_name"]
        last_name = data["last_name"]

        # Optional parameters with defaults
        layout = data.get("layout", "side_by_side")  # 'side_by_side' or 'stacked'
        font_size = data.get("font_size", 100)
        padding = data.get("padding", 10)

        # Print debug info
        print(f"Creating dynamic label for: {first_name} {last_name}")
        print(f"Layout: {layout}, Font size: {font_size}, Padding: {padding}")
        print(f"Using printer: {printer_state.get('address', 'Not connected')}")

        # Create the label with dynamic sizing
        image_path, dimensions = create_dynamic_label(
            first_name, last_name, layout=layout, font_size=font_size, padding=padding
        )

        # Print the image - pass the printer address from the global state
        printer_address = (
            printer_state.get("address")
            if printer_state.get("connected", False)
            else None
        )
        print_success = print_name(image_path, printer_address)

        return (
            jsonify(
                {
                    "message": "Print initiated",
                    "success": print_success,
                    "printer": printer_address,
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "image_path": image_path,
                        "layout": layout,
                        "font_size": font_size,
                        "width": dimensions[0],
                        "height": dimensions[1],
                    },
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error in print-dynamic endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/print-simple", methods=["POST"])
def handle_print_simple():
    try:
        global printer_state
        data = request.get_json()

        # Required parameters
        if "first_name" not in data or "last_name" not in data:
            return jsonify({"error": "Missing first or last name in request body"}), 400

        first_name = data["first_name"]
        last_name = data["last_name"]

        # Optional parameters with defaults
        layout = data.get("layout", "side_by_side")  # 'side_by_side' or 'stacked'
        font_size = data.get("font_size", 300)
        width = data.get("width", 731)  # 62mm at 300dpi
        height = data.get("height", 300)

        # Print debug info
        print(f"Creating simple label for: {first_name} {last_name}")
        print(f"Layout: {layout}, Font size: {font_size}")
        print(f"Dimensions: {width}x{height}")
        print(f"Using printer: {printer_state.get('address', 'Not connected')}")

        # Create the label
        image_path = create_simple_label(
            first_name,
            last_name,
            layout=layout,
            font_size=font_size,
            width=width,
            height=height,
        )

        # Print the image - pass the printer address from the global state
        printer_address = (
            printer_state.get("address")
            if printer_state.get("connected", False)
            else None
        )
        print_success = print_name(image_path, printer_address)

        return (
            jsonify(
                {
                    "message": "Print initiated",
                    "success": print_success,
                    "printer": printer_address,
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "image_path": image_path,
                        "layout": layout,
                        "font_size": font_size,
                        "width": width,
                        "height": height,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error in print-simple endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Maintain the old endpoints for backward compatibility
@app.route("/print-name", methods=["POST"])
def handle_print_name():
    try:
        global printer_state
        data = request.get_json()

        # Required parameters
        if "attendee_firstname" not in data or "attendee_lastname" not in data:
            return jsonify({"error": "Missing first or last name in request body"}), 400

        first_name = data["attendee_firstname"]
        last_name = data["attendee_lastname"]

        # Use font size if provided, otherwise default to 400 which worked well
        font_size = data.get("font_size", 400)

        # Create dynamic label
        image_path, dimensions = create_dynamic_label(
            first_name,
            last_name,
            layout=data.get("layout", "side_by_side"),
            font_size=font_size,
            padding=data.get("padding", 10),
        )

        # Print the image - pass the printer address from the global state
        printer_address = (
            printer_state.get("address")
            if printer_state.get("connected", False)
            else None
        )
        print_success = print_name(image_path, printer_address)

        return (
            jsonify(
                {
                    "message": "Print initiated",
                    "success": print_success,
                    "printer": printer_address,
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "image_path": image_path,
                        "width": dimensions[0],
                        "height": dimensions[1],
                    },
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error in print-name endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=True)
