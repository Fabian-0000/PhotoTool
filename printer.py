import subprocess
import json

import threading

sumatra_path = r"extern/SumatraPDF-3.6-64/SumatraPDF-3.6-64.exe"

def print_job(printer: str, file: str):
    try:
        subprocess.run([
            sumatra_path,
            "-print-to",
            printer,
            file
        ], check=True)
    except Exception as e:
        print("Error:", e)

def print_doc(path: str):
    data = None
    try:
        # Open the JSON file
        with open('settings.json', 'r') as file:
            data = json.load(file)
    except:
        pass

    if not data['enabled']:
        return
    
    threading.Thread(target=print_job, args = (data['printer'], path)).start()