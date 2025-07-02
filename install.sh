#!/bin/bash

apt update
apt install python3 -y
apt install python3-pip -y
pip install azure-identity --break-system-packages
pip install azure-storage-blob --break-system-packages
pip install semantic-kernel --break-system-packages