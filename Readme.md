# Simple Label Printer System

A streamlined Flask-based web application for connecting to and printing custom labels on Brother QL label printers with clean, straightforward customization options.

## Features

- **Printer Connection Management**
  - Scan for available system printers
  - Connect to selected printer
  - Maintain printer connection state between sessions
  - Monitor connection status

- **Simple Label Generation**
  - Fixed dimensions with exact font sizes
  - Side-by-side or stacked name layout
  - Center-aligned text both horizontally and vertically
  - Fully configurable dimensions and font sizes

- **Web Interfaces**
  - Main printer management interface
  - Testing interface for label configuration

## Setup & Requirements

1. Install required packages:
   ```
   pip install -r requirements.txt
   ```

2. Ensure your Brother QL label printer is installed on your system

3. Run the application:
   ```
   python main.py
   ```

4. Access the web interface at: `http://localhost:5555`

## File Structure

- **main.py**: Application entry point
- **routes.py**: API endpoints and routes definition
- **functions.py**: Core label generation and printing functions
- **printer_manager/**: Printer connection utilities
  - **connection.py**: Printer connection testing and management
  - **scanner.py**: System printer detection

## Web Interfaces

- **/** - Main interface for printer management
- **/test** - Label printer test interface

Access the test web interface at: `http://localhost:5555/test`



## API Endpoints

### Printer Management

- **GET /api/printer/status**
  - Returns current printer connection status

- **POST /api/printer/scan/system**
  - Scans for available system printers

- **POST /api/printer/connect**
  - Connects to specified printer
  - Required JSON parameters:
    - `method`: Connection method (currently only "system" is supported)
    - `address`: Printer name/address

### Label Printing

- **POST /print-simple**
  - Prints a label with fixed dimensions
  - Required JSON parameters:
    - `first_name`: First name
    - `last_name`: Last name
  - Optional parameters:
    - `layout`: "side_by_side" or "stacked" (default: "side_by_side")
    - `font_size`: Exact font size to use (default: 300)
    - `width`: Label width in pixels (default: 731)
    - `height`: Label height in pixels (default: 300)

## Label Function

### create_simple_label

Creates a label with fixed dimensions and exact font size.

```python
create_simple_label(first_name, last_name, layout="side_by_side", font_size=300, width=731, height=300)
```

- **Parameters**:
  - `first_name`: First name to print
  - `last_name`: Last name to print
  - `layout`: Either "side_by_side" or "stacked"
  - `font_size`: Exact font size to use (no auto-scaling)
  - `width`: Label width in pixels
  - `height`: Label height in pixels

- **Returns**: Path to the created image file

## Printing Function

### print_name

Sends the generated label image to the printer.

```python
print_name(path, printer_address=None)
```

- **Parameters**:
  - `path`: Path to the image file to print
  - `printer_address`: Printer address to use (optional - uses selected printer if not specified)

- **Returns**: True if print was successful, False otherwise

## Recommended Settings

For best results with Brother QL-820NWB label printer:
- Width: 731px (62mm at 300 DPI)
- Height: 300px for standard labels
- Font size: 300-500 for most names
- Layout: "side_by_side" for shorter names, "stacked" for longer names

## Notes

- The system supports different label printers but is primarily designed for the Brother QL-820NWB
- Images are temporarily stored in the `img/` folder
- Printer connection state is saved in `printer_state.json`