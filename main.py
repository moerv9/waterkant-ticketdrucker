# Import the app from routes
from routes import app

# Run the application
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5555, debug=True)