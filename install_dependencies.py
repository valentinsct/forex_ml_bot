import os
import platform
import subprocess
import sys

def install_talib():
    system = platform.system()

    try:
        if system == "Windows":
            # RUTA a la versión .whl de Windows (modifícala según tus necesidades)
            wheel_path = "./libs/TA_Lib-0.4.24-cp38-cp38-win_amd64.whl"
            subprocess.check_call([sys.executable, "-m", "pip", "install", wheel_path])
        
        elif system == "Linux":
            # Instalar dependencias de TA-Lib en Linux
            subprocess.check_call(["sudo", "apt-get", "install", "-y", "libta-lib0", "libta-lib-dev"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "TA-Lib"])

        elif system == "Darwin":  # macOS
            # Instalar dependencias de TA-Lib en macOS
            subprocess.check_call(["brew", "install", "ta-lib"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "TA-Lib"])

        print("TA-Lib instalado correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"Error al instalar TA-Lib: {e}")
        sys.exit(1)

def install_requirements():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError as e:
        print(f"Error al instalar las dependencias: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_requirements()
    install_talib()