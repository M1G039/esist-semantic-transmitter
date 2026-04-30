#!/usr/bin/env bash
set -x
set -euo pipefail

BASE_DIR="/home/guilherme"

# this script initiates
echo "[*] Initializing Docker Container for Mosquitto Broker..."
echo 
sleep 3

# creating a backup directory
BACKUP_DIR="${HOME}/backup_$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
echo 
echo "[+] Backup will be stored in $BACKUP_DIR"
echo

sleep 2

CONFIG_DIR=$BASE_DIR/"mosquitto.conf"

if [[ ! -f "$CONFIG_DIR" ]]; then
	echo "[x] Config file $CONFIG_DIR not found"
	exit 1
fi

# run the container
docker run -d \
  --name mosquitto \
  -p 1883:1883 \
  -p 8883:8883 \
  -v "$CONFIG_DIR:/mosquitto/config/mosquitto.conf":ro \
  eclipse-mosquitto

# success confirmation
sleep 1
echo ""
echo "[*] Docker running!"
