# Flask Application Runner Script
$venvPath = "./venv/bin/Activate.ps1"

# Check if venv exists
if (-Not (Test-Path $venvPath)) {
Write-Host "Virtual environment not found. Creating one..."
python3 -m venv venv
}

# Activate venv
Write-Host "Activating virtual environment..."
& $venvPath

# Install dependencies
Write-Host "Installing dependencies..."
pip install -q -r requirements.txt

# Run Flask app
Write-Host "Starting Flask application on http://localhost:5000"
Write-Host "Press Ctrl+C to stop the server"
python3 app.py
