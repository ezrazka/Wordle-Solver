set -e

echo "Creating virtual environment..."
python3 -m venv env

echo "Activating virtual environment..."
source env/bin/activate

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Running project..."
python3 main.py