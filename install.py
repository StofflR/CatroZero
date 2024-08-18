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
USB_SIZE = "8G"

ARCH = subprocess.run(["dpkg", "--print-architecture"], capture_output=True, text=True).stdout.strip()
OBEX_FILE = f"obexpushd_0.11.2-4_{ARCH}.deb"


# Argument parser setup
parser = argparse.ArgumentParser(description="Parse program arguments.")
parser.add_argument("--delay", type=int, default=DELAY, help="Delay in seconds")
parser.add_argument("--hostname", type=str, default=HOSTNAME, help="Hostname")
parser.add_argument("--wifi-path", type=str, default=WIFI_PATH, help="WiFi path")
parser.add_argument("--bluetooth-path", type=str, default=BLUETOOTH_PATH, help="Bluetooth path")
parser.add_argument("--mount-file", type=str, default=MOUNT_FILE, help="Mount file path")
parser.add_argument("--data-file", type=str, default=DATA_FILE, help="Data file path")
parser.add_argument("--usb-size", type=str, default=USB_SIZE, help="USB size e.g. 8.0G or 8M")
parser.add_argument("--venv", type=str, default=VENV_PATH, help="Path to python virtual environment bin folder e.g. .venv/bin")

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
PYTHON = path.join(VENV_PATH, "python3")

# Print values to verify
print(f"DELAY: {DELAY}")
print(f"HOSTNAME: {HOSTNAME}")
print(f"WIFI_PATH: {WIFI_PATH}")
print(f"BLUETOOTH_PATH: {BLUETOOTH_PATH}")
print(f"MOUNT_FILE: {MOUNT_FILE}")
print(f"DATA_FILE: {DATA_FILE}")
print(f"USB_SIZE: {USB_SIZE}")
print(f"VENV: {VENV_PATH}")#

PWD_KEY = "PWD"
DEL_KEY = "DEL"
WFILE_KEY = "WFILE"
BLFILE_KEY = "BLFILE"
MNTFILE_KEY = "MNTFILE"
DATAFILE_KEY = "DATAFILE"
HOSTNAME_KEY = "HOSTNAME"

configuration = {
    PWD_KEY: re.sub(r'[\/&]', r'\\\g<0>', getcwd()),
    DEL_KEY: str(DELAY),
    WFILE_KEY: re.sub(r'[\/&]', r'\\\g<0>', WIFI_PATH),
    BLFILE_KEY: re.sub(r'[\/&]', r'\\\g<0>', BLUETOOTH_PATH),
    MNTFILE_KEY: re.sub(r'[\/&]', r'\\\g<0>', MOUNT_FILE),
    DATAFILE_KEY: re.sub(r'[\/&]', r'\\\g<0>', DATA_FILE),
    HOSTNAME_KEY: HOSTNAME
}

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

def display_loading_symbol(text, stop):
    symbols = ['-', '\\', '|', '/']
    i = 0
    while True:
        print(f"{text} ... {symbols[i]}", end='\r')
        i = (i + 1) % len(symbols)
        if stop():
            return
        time.sleep(0.1)

def run_command(commands, display):
    stop_thread = False
    loading_thread = threading.Thread(target=display_loading_symbol, args=[display, lambda: stop_thread])
    loading_thread.start()
    for command in commands:
        subprocess.run(command)
    stop_thread = True
    loading_thread.join()

run_command([["fallocate", "-l", USB_SIZE, DATA_FILE]], "Creating shared usb file")
run_command([["mkfs.vfat", "-F32", DATA_FILE]], "Formating shared usb file")


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

run_command([["apt-get", "update"], 
             ["apt-get", "upgrade", "-y", "--fix-missing"], 
             ["apt-get", "install", "samba", "screen", "-y"],
             ["apt-get", "install", "libbluetooth3", "python3-dev", "libdbus-1-dev", "libc6", "libwrap0", "pulseaudio-module-bluetooth", "libglib2.0-dev", "libcairo2-dev", "libgirepository1.0-dev", "-y"],
             ["apt-get", "install", "libopenobex2", "obexpushd", "-y"]], "Installing dependencies")

# Check if libopenobex2 is already installed 

if subprocess.run(["dpkg", "-s", "libopenobex2"], capture_output=True).returncode != 0 or subprocess.run(["dpkg", "-s", "obexpushd"], capture_output=True).returncode != 0:
    print("obex error!")

    subprocess.run(["apt-get", "install", "libopenobex2", "-y"])
    
    print("Trying manual installation!")
    subprocess.run(["wget", f"http://ftp.at.debian.org/debian/pool/main/o/obexpushd/{OBEX_FILE}"])
    subprocess.run(["dpkg", "-i", f"{OBEX_FILE}"])
    remove(f"{OBEX_FILE}")

subprocess.run(["apt-get", "install", "--fix-broken", "-y"])
subprocess.run([PYTHON, "-m" ,"pip", "install", "watchdog", "dbus-python", "PyGObject"])


makedirs(MOUNT_FILE, mode=0o2777, exist_ok=True)
run_command([["mount", DATA_FILE, MOUNT_FILE]], "Mounting USB Storage to shared folder")


print("Creating network shared folder")
makedirs(WIFI_PATH, mode=0o2777, exist_ok=True)

def create_backup(file):
    backup = f"{file}.bak"
    if not path.exists(backup):
        shutil.copy(file, backup)
        return True
    return False

def restore_backup(file):
    backup = f"{file}.bak"
    if path.exists(backup):
        shutil.copy(backup, file)

samba_config = "/etc/samba/smb.conf"
if not create_backup(samba_config):
    restore_backup(samba_config)

if str.lower(configuration[HOSTNAME_KEY]) not in open(samba_config).read():
    with open("samba_config.txt", "r") as file:
        line = file.read().replace(WFILE_KEY, configuration[WFILE_KEY])
        line = line.replace(HOSTNAME_KEY, str.lower(configuration[HOSTNAME_KEY]))
        with open(samba_config, "a") as config_file:
            config_file.write(line)

print("Setting Bluetooth device name")
with open(path.join(getcwd(), 'main.conf'), 'r') as file:
    file.write(file.read().replace(HOSTNAME_KEY, configuration[HOSTNAME_KEY]))

shutil.copy(f"{getcwd()}/main.conf", "/etc/bluetooth/main.conf")

def set_compat(file, target):
    with open(file, "r") as file:
        if ' -C' in file.read():
            print("Already in compat mode")
        else:
            print(f"Set {target} to compat mode")
            with open(file, "r+") as file:
                lines = file.readlines()
                execnum = next(i for i, line in enumerate(lines) if "ExecStart" in line)
                lines[execnum] = lines[execnum].strip() + " -C\n"
                file.seek(0)
                file.writelines(lines)

# Check if ' -C' is already present
set_compat("/etc/systemd/system/dbus-org.bluez.service", "bluez")
set_compat("/etc/systemd/system/bluetooth.target.wants/bluetooth.service", "target.wants.bluetooth")
set_compat("/lib/systemd/system/bluetooth.service", "system/bluetooth")


# Read the contents of the boot_config.txt file
with open(path.join(getcwd(), 'boot_config.txt'), 'r') as file:
    line = file.read()

    for placeholder, path in configuration.items():
        line =  re.sub(placeholder, path, line)

    with open(path.join(getcwd(), 'boot.sh'), 'w') as file:
        file.write(line)


chmod(path.join(getcwd(), "boot.sh"), mode=0o755)
shutil.copy(path.join(getcwd(), "boot.sh"), "/usr/local/bin/catropi.sh")
chmod("/usr/local/bin/catropi.sh", mode=0o755)

service_file = path.join(getcwd(), "catropi.service")
destination = "/etc/systemd/system/catropi.service"
shutil.copy(service_file, destination)
chmod(destination, mode=0o640)

subprocess.run(["systemctl", "enable", "catropi.service"])
subprocess.run(["bluetoothctl", "system-alias", HOSTNAME])
subprocess.run(["hostnamectl", "set-hostname", HOSTNAME])
subprocess.run(["hciconfig", "hci0", "class", "100100"])