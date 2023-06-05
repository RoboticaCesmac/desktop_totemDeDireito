#!/bin/bash
# conecta.sh
# navigate to home directory, then to this directory, then execute python script, then back home



cd /
cd home/pi/Desktop/Conecta
sudo -u root pulseaudio --start 
start-pulseaudio-x11
export DISPLAY=:0.0
sudo python main.py
cd /


