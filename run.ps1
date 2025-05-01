# Activate the virtual environment
& ".\venv\Scripts\Activate.ps1"

# Set environment variables
$env:FLASK_APP = "main.py"
$env:FLASK_ENV = "development"

# Open the default browser to your Flask site (localhost:5000)
Start-Process "http://127.0.0.1:5000"

# Print to terminal
Write-Host "Flask server starting..."

# Run Flask app
python main.py

# After server stops
Write-Host "Server stopped. Press any key to close..."
$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
