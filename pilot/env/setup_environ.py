import subprocess
import os

curdir = os.path.dirname(os.path.realpath(__file__))
subprocess.call(
    [
        "C:\\WINDOWS\\system32\\WindowsPowerShell\\v1.0\\powershell.exe",
        f"& 'C:\\Program Files\\Alteryx\\bin\\Miniconda3\\python.exe' -m venv {curdir}",
    ]
)
subprocess.call(
    [
        "C:\\WINDOWS\\system32\\WindowsPowerShell\\v1.0\\powershell.exe",
        f"& '{os.path.join(curdir,'Scripts','pip.exe')}' install -r '{os.path.join(curdir,'requirements.txt')}'",
    ]
)
