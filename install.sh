#!/bin/bash

delay=5
hostname="CatroZero"
wififile=$PWD"/wifi"
blfile=$PWD"/bluetooth"
mountfile="/mnt/piusb"
datafile="/piusb.bin"

if [ "$USER" != "root" ]
then
    echo "Please run this as root or with sudo"
    exit 2
fi

echo "127.0.0.1	$hostname" | sudo tee -a /etc/hosts
mkdir bluetooth
mkdir wifi

loading(){
    pid=$!
    spin='-\|/'
    i=0
    while kill -0 $pid 2>/dev/null
    do
    i=$(( (i+1) %4 ))
    printf "This might take a while! \r${spin:$i:1}"
    sleep .1
    done
    echo ""
}

echo "Creating shared usb file"
dd if=/dev/zero of=$datafile bs=1M count=8K &
loading

echo "Formating shared usb file"
mkfs.vfat -F32 $datafile &
loading

echo "Enabeling USB OTG mass storage"
if [ ! -z $(grep "dtoverlay=dwc2" "/boot/config.txt") ];
    then echo "Already enabled dwc2";
    else echo "dtoverlay=dwc2" | sudo tee -a /boot/config.txt;
fi

if [ ! -z $(grep "dwc2" "/etc/modules") ];
    then echo "Already enabled dwc2";
    else echo "dwc2" | sudo tee -a /etc/modules;
fi

if [ ! -z $(grep "g_mass_storage" "/etc/modules") ];
    then echo "Already enabled g_mass_storage";
    else echo "g_mass_storage" | sudo tee -a /etc/modules;
fi

echo "Installing dependencies"
apt-get update
apt-get upgrade -y --fix-missing
apt-get install samba screen python3 python3-pip -y
apt-get install libbluetooth3 python3-dev libdbus-1-dev libc6 libwrap0 pulseaudio-module-bluetooth libglib2.0-dev libcairo2-dev libgirepository1.0-dev -y
apt-get install libopenobex2 obexpushd -y

if [ $? -eq 0 ];
    then echo "Obex installed sucessfully!";
    else
        apt-get install libopenobex2 -y
        arch=$(dpkg --print-architecture)
        echo "Trying manuall installation!"
        wget "http://ftp.at.debian.org/debian/pool/main/o/obexpushd/obexpushd_0.11.2-1.1+b1_$arch.deb"
        dpkg -i "obexpushd_0.11.2-1.1+b1_$arch.deb"
        rm "obexpushd_0.11.2-1.1+b1_$arch.deb";
fi
apt-get install --fix-broken -y


python_version=$(python --version | tr '\n' ' ' | sed -e 's/[^0-9]/ /g' -e 's/^ *//g' -e 's/ *$//g' | tr -s ' ' | sed 's/ / /g' | awk '{print $2}')
sudo rm /usr/lib/python3.$python_version/EXTERNALLY-MANAGED

echo "Installing watchdog"
pip3 install watchdog
echo "Installing dbus-python"
pip3 install dbus-python
echo "Installing PyGObject"
pip3 install PyGObject

echo "Mountig USB Storage to shared folder"
mkdir -m 2777 $mountfile
mount $datafile $mountfile

echo "Creating network shared folder"
mkdir -m 2777 $wififile

if [ ! -z $(grep "pi-share" "/etc/samba/smb.conf") ];
    then echo "Already created samba config";
    else
	line=$(cat $PWD/samba_config.txt)
        ESCAPED_PATH=$(printf '%s\n' "$wififile" | sed -e 's/[\/&]/\\&/g')
        line=$(echo "$line" | sed "s/WIFIFILE/$ESCAPED_PATH/g")
        echo "$line" | tee -a /etc/samba/smb.conf;
fi

echo "Setting Bluetooth device name"
cp $PWD/main.conf /etc/bluetooth/main.conf

if grep -q ' -C' "/etc/systemd/system/dbus-org.bluez.service";
    then echo "Already in compat mode";
    else
        echo "Set bluetoothd to compat mode"
        execnum=$(sed -n "/ExecStart/=" /etc/systemd/system/dbus-org.bluez.service)
        sed "$execnum s/.*/& -C/" /etc/systemd/system/dbus-org.bluez.service
        sed -i "$execnum s/.*/& -C/" /etc/systemd/system/dbus-org.bluez.service;
fi

if grep -q ' -C' "/etc/systemd/system/bluetooth.target.wants/bluetooth.service";
    then echo "Already in compat mode";
    else
        echo "Set bluetoothd to compat mode"
        execnum=$(sed -n "/ExecStart/=" /etc/systemd/system/bluetooth.target.wants/bluetooth.service)
        sed "$execnum s/.*/& -C/" /etc/systemd/system/bluetooth.target.wants/bluetooth.service
        sed -i "$execnum s/.*/& -C/" /etc/systemd/system/bluetooth.target.wants/bluetooth.service;
fi

if grep -q ' -C' "/lib/systemd/system/bluetooth.service";
    then echo "Already in compat mode";
    else
        echo "Set bluetoothd to compat mode"
        execnum=$(sed -n "/ExecStart/=" /lib/systemd/system/bluetooth.service)
        sed "$execnum s/.*/& -C/" /lib/systemd/system/bluetooth.service
        sed -i "$execnum s/.*/& -C/" /lib/systemd/system/bluetooth.service;
fi
echo "Adding startup commands"

delsym="d"
exitnum=$(echo "$(sed -n "/exit 0/=" /etc/rc.local)" | tail -n1)
sed -i "$exitnum$delsym" /etc/rc.local

ESCAPED_PATH=$(printf '%s\n' "$PWD" | sed -e 's/[\/&]/\\&/g')
line=$(sed "s/PWD/$ESCAPED_PATH/g" $PWD/boot_config.txt)
line=$(echo "$line" | sed "s/DEL/$delay/g")
ESCAPED_PATH=$(printf '%s\n' "$wififile" | sed -e 's/[\/&]/\\&/g')
line=$(echo "$line" | sed "s/WFILE/$ESCAPED_PATH/g")
ESCAPED_PATH=$(printf '%s\n' "$blfile" | sed -e 's/[\/&]/\\&/g')
line=$(echo "$line" | sed "s/BLFILE/$ESCAPED_PATH/g")
ESCAPED_PATH=$(printf '%s\n' "$mountfile" | sed -e 's/[\/&]/\\&/g')
line=$(echo "$line" | sed "s/MNTFILE/$ESCAPED_PATH/g")
ESCAPED_PATH=$(printf '%s\n' "$datafile" | sed -e 's/[\/&]/\\&/g')
line=$(echo "$line" | sed "s/DATAFILE/$ESCAPED_PATH/g")

touch $PWD/boot.sh
if [ ! $? -eq 0 ];
    then
        rm $PWD/boot.sh
        touch $PWD/boot.sh;
fi
echo "$line" | sudo tee ./boot.sh

chmod +x $PWD/boot.sh
cp $PWD/boot.sh /usr/local/bin/catropi.sh
chmod +x /usr/local/bin/catropi.sh
cp $PWD/catropi.service /etc/systemd/system/catropi.service
chmod 640 /etc/systemd/system/catropi.service
systemctl enable catropi.service

bluetoothctl system-alias $hostname
hostnamectl set-hostname $hostname
hciconfig hci0 class 100100