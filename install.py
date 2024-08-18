from os import getcwd, mkdir, path, geteuid, chmod, makedirs, remove
import subprocess
import time
import threading
import sys
import re
import shutil
import argparse
from os import getcwd, path

# Default values
DELAY = 5
HOSTNAME = "CatroZero"
WIFI_PATH = path.join(getcwd(), "wifi")
BLUETOOTH_PATH = path.join(getcwd(), "bluetooth")
MOUNT_FILE = "/mnt/pi_usb"
DATA_FILE = "/pi_usb.bin"
VENV_PATH = path.join(getcwd(), ".venv/bin")

USB_SIZE = "8G"   # 8GB

# Argument parser setup
parser = argparse.ArgumentParser(description="Parse program arguments.")
parser.add_argument("--delay", type=int, default=DELAY, help="Delay in seconds")
parser.add_argument("--hostname", type=str, default=HOSTNAME, help="Hostname")
parser.add_argument("--wifi-path", type=str, default=WIFI_PATH, help="WiFi path")
parser.add_argument("--bluetooth-path", type=str, default=BLUETOOTH_PATH, help="Bluetooth path")
parser.add_argument("--mount-file", type=str, default=MOUNT_FILE, help="Mount file path")
parser.add_argument("--data-file", type=str, default=DATA_FILE, help="Data file path")
parser.add_argument("--usb-size", type=str, default=USB_SIZE, help="USB size e.g. 8.0G or 8M")
parser.add_argument("--venv", type=str, default=VENV_PATH, help="Path to python virtual environment")

# Parse arguments
args = parser.parse_args()

# Assign parsed values to variables
DELAY = args.delay
HOSTNAME = args.hostname
WIFI_PATH = args.wifi_path
BLUETOOTH_PATH = args.bluetooth_path
MOUNT_FILE = args.mount_file
DATA_FILE = args.data_file
USB_SIZE = args.usb_size

# Print values to verify
print(f"DELAY: {DELAY}")
print(f"HOSTNAME: {HOSTNAME}")
print(f"WIFI_PATH: {WIFI_PATH}")
print(f"BLUETOOTH_PATH: {BLUETOOTH_PATH}")
print(f"MOUNT_FILE: {MOUNT_FILE}")
print(f"DATA_FILE: {DATA_FILE}")
print(f"USB_SIZE: {USB_SIZE}")
print(f"VENV: {VENV_PATH}")


if geteuid() != 0:
    print("Please run this script as root.")
    exit(1)

if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("Python is running in a virtual environment.")
else:
    print("Python is not running in a virtual environment.")
    exit(1)

if not path.exists(BLUETOOTH_PATH):
    mkdir(BLUETOOTH_PATH)

if not path.exists(WIFI_PATH):
    mkdir(WIFI_PATH)

hosts_entry = f"127.0.0.1\t{HOSTNAME}"
with open("/etc/hosts", "a") as hosts_file:
    hosts_file.write(hosts_entry + "\n")

def display_loading_symbol(text):
    symbols = ['-', '\\', '|', '/']
    i = 0
    while True:
        print(f"{text} ... {symbols[i]}", end='\r')
        i = (i + 1) % len(symbols)
        time.sleep(0.1)

loading_thread = threading.Thread(target=display_loading_symbol, args=["Creating shared usb file"])
loading_thread.start()

subprocess.run(["fallocate", "-l", USB_SIZE ,DATA_FILE])

loading_thread.join()

loading_thread = threading.Thread(target=display_loading_symbol, args=["Formating shared usb file"])
loading_thread.start()

subprocess.run(["mkfs.vfat", "-F32", DATA_FILE])

loading_thread.join()
config_file = "/boot/config.txt"
dtoverlay_line = "dtoverlay=dwc2"

# Check if "dtoverlay=dwc2" is already enabled in /boot/config.txt
if dtoverlay_line in open(config_file).read():
    print("Already enabled dwc2")
else:
    # Append "dtoverlay=dwc2" to /boot/config.txt
    with open(config_file, "a") as file:
        file.write(dtoverlay_line + "\n")

# Check if "dwc2" is already enabled in /etc/modules
if "dwc2" in open("/etc/modules").read():
    print("Already enabled dwc2")
else:
    # Append "dwc2" to /etc/modules
    with open("/etc/modules", "a") as modules_file:
        modules_file.write("dwc2\n")

# Check if "g_mass_storage" is already enabled in /etc/modules
if "g_mass_storage" in open("/etc/modules").read():
    print("Already enabled g_mass_storage")
else:
    # Append "g_mass_storage" to /etc/modules
    with open("/etc/modules", "a") as modules_file:
        modules_file.write("g_mass_storage\n")

loading_thread = threading.Thread(target=display_loading_symbol, args=["Installing dependencies",])
loading_thread.start()

subprocess.run(["apt-get", "update"])
subprocess.run(["apt-get", "upgrade", "-y", "--fix-missing"])
subprocess.run(["apt-get", "install", "samba", "screen", "python3", "python3-pip", "-y"])
subprocess.run(["apt-get", "install", "libbluetooth3", "python3-dev", "libdbus-1-dev", "libc6", "libwrap0", "pulseaudio-module-bluetooth", "libglib2.0-dev", "libcairo2-dev", "libgirepository1.0-dev", "-y"])
subprocess.run(["apt-get", "install", "libopenobex2", "obexpushd", "-y"])

loading_thread.join()

# Check if libopenobex2 is already installed
result = subprocess.run(["dpkg", "-s", "libopenobex2"], capture_output=True)
result += subprocess.run(["dpkg", "-s", "obexpushd"], capture_output=True)

if result.returncode == 0:
    print("libopenobex2 is already installed")
else:
    print("libopenobex2 is not installed")
    subprocess.run(["apt-get", "install", "libopenobex2", "-y"])

    # Check if libopenobex2 is already installed
    result = subprocess.run(["dpkg", "-s", "libopenobex2"], capture_output=True)
    if result.returncode == 0:
        print("libopenobex2 is already installed")
    else:
        print("libopenobex2 is not installed")
        subprocess.run(["apt-get", "install", "libopenobex2", "-y"])
        arch = subprocess.run(["dpkg", "--print-architecture"], capture_output=True, text=True).stdout.strip()
        print("Trying manual installation!")
        subprocess.run(["wget", f"http://ftp.at.debian.org/debian/pool/main/o/obexpushd/obexpushd_0.11.2-1.1+b1_{arch}.deb"])
        subprocess.run(["dpkg", "-i", f"obexpushd_0.11.2-1.1+b1_{arch}.deb"])
        remove(f"obexpushd_0.11.2-1.1+b1_{arch}.deb")

subprocess.run(["apt-get", "install", "--fix-broken", "-y"])

python_minor_version = sys.version_info.minor
print(f"Python minor version: {python_minor_version}")

subprocess.run(["pip3", "install", "watchdog", "dbus-python", "PyGObject"])

loading_thread = threading.Thread(target=display_loading_symbol, args=["Mounting USB Storage to shared folder",])
loading_thread.start()

makedirs(MOUNT_FILE, mode=0o2777)
subprocess.run(["mount", DATA_FILE, MOUNT_FILE])

loading_thread.join()

loading_thread = threading.Thread(target=display_loading_symbol, args=["Creating network shared folder",])
loading_thread.start()

makedirs(WIFI_PATH, mode=0o2777)

loading_thread.join()

samba_config = "/etc/samba/smb.conf"
sample_config = "/etc/samba/smb.conf.sample"

if not path.exists(sample_config):
    shutil.copy(samba_config, sample_config)


if "pi-share" in open(samba_config).read():
    print("Already created samba config - falling back to default")
    shutil.rmtree(samba_config)
    shutil.copy(sample_config, samba_config)

with open("samba_config.txt", "r") as file:
    line = file.read()
    escaped_path = WIFI_PATH.replace("/", "\\/")
    line = line.replace("WIFIFILE", escaped_path)
    with open(samba_config, "a") as config_file:
        config_file.write(line)

loading_thread = threading.Thread(target=display_loading_symbol, args=["Setting Bluetooth device name",])
loading_thread.start()


with open(path.join(getcwd(), 'main.conf'), 'r') as file:
    file.write(file.read().replace('HOSTNAME', HOSTNAME))

shutil.copy(f"{getcwd()}/main.conf", "/etc/bluetooth/main.conf")

loading_thread.join()

# Check if ' -C' is already present in "/etc/systemd/system/dbus-org.bluez.service"
with open("/etc/systemd/system/dbus-org.bluez.service", "r") as file:
    if ' -C' in file.read():
        print("Already in compat mode")
    else:
        print("Set bluetoothd to compat mode")
        with open("/etc/systemd/system/dbus-org.bluez.service", "r+") as file:
            lines = file.readlines()
            execnum = next(i for i, line in enumerate(lines) if "ExecStart" in line)
            lines[execnum] = lines[execnum].strip() + " -C\n"
            file.seek(0)
            file.writelines(lines)

# Check if ' -C' is already present in "/etc/systemd/system/bluetooth.target.wants/bluetooth.service"
with open("/etc/systemd/system/bluetooth.target.wants/bluetooth.service", "r+") as file:
    if ' -C' in file.read():
        print("Already in compat mode")
    else:
        print("Set bluetoothd to compat mode")
        lines = file.readlines()
        execnum = next(i for i, line in enumerate(lines) if "ExecStart" in line)
        lines[execnum] = lines[execnum].strip() + " -C\n"
        file.seek(0)
        file.writelines(lines)

bluetooth_service_file = "/lib/systemd/system/bluetooth.service"
with open(bluetooth_service_file, "r") as file:
    if ' -C' in file.read():
        print("Already in compat mode")
    else:
        with open(bluetooth_service_file, "r+") as file:
            print("Set bluetoothd to compat mode")
            lines = file.readlines()
            execnum = next(i for i, line in enumerate(lines) if "ExecStart" in line)
            lines[execnum] = lines[execnum].strip() + " -C\n"
            file.seek(0)
            file.writelines(lines)


# Escape special characters in the current working directory path
escaped_path = re.sub(r'[\/&]', r'\\\g<0>', getcwd())

# Read the contents of the boot_config.txt file
with open(path.join(getcwd(), 'boot_config.txt'), 'r') as file:
    line = file.read()

    # Replace the placeholder PWD with the escaped current working directory path
    line = re.sub(r'PWD', escaped_path, line)

    # Replace the placeholder DEL with the delay value
    line = re.sub(r'DEL', str(DELAY), line)

    # Replace the placeholder WFILE with the escaped wifi file path
    line = re.sub(r'WFILE', re.sub(r'[\/&]', r'\\\g<0>', WIFI_PATH), line)

    # Replace the placeholder BLFILE with the escaped bluetooth file path
    line = re.sub(r'BLFILE', re.sub(r'[\/&]', r'\\\g<0>', BLUETOOTH_PATH), line)

    # Replace the placeholder MNTFILE with the escaped mount file path
    line = re.sub(r'MNTFILE', re.sub(r'[\/&]', r'\\\g<0>', MOUNT_FILE), line)

    # Replace the placeholder DATAFILE with the escaped data file path
    line = re.sub(r'DATAFILE', re.sub(r'[\/&]', r'\\\g<0>', DATA_FILE), line)

    # Replace the placeholder DATAFILE with the escaped data file path
    line = re.sub(r'HOSTNAME', re.sub(r'[\/&]', r'\\\g<0>', HOSTNAME), line)

    with open(path.join(getcwd(), 'boot.sh'), 'w') as file:
        file.write(line)


chmod(path.join(getcwd(), "boot.sh"), mode=0o755)
shutil.copy(f"{getcwd()}/boot.sh", "/usr/local/bin/catropi.sh")
chmod("/usr/local/bin/catropi.sh", mode=0o755)

service_file = f"{getcwd()}/catropi.service"
destination = "/etc/systemd/system/catropi.service"
shutil.copy(service_file, destination)
chmod(destination, mode=0o640)

subprocess.run(["systemctl", "enable", "catropi.service"])
subprocess.run(["bluetoothctl", "system-alias", HOSTNAME])
subprocess.run(["hostnamectl", "set-hostname", HOSTNAME])
subprocess.run(["hciconfig", "hci0", "class", "100100"])