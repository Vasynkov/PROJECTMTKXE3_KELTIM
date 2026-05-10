import subprocess
import sys
import os

def run():
    print("Checking dependencies...")
    try:
        import flask
    except ImportError:
        print("Installing Flask...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    if not os.path.exists('trigonometri.db'):
        print("Setting up database...")
        subprocess.check_call([sys.executable, "database_setup.py"])
    
    print("Starting ProjectTrigonometri_X-e3-kelTIM...")
    print("Akses website di: http://127.0.0.1:5000")
    subprocess.check_call([sys.executable, "app.py"])

if __name__ == "__main__":
    run()
