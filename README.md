<div align="center">

### **Sharp NEC HomeKit TV** <!-- omit in toc -->

_...convert an awesome raspberry pi commercial display into a homekit tv and remote_

<img src="https://github.com/ground7/sharp-nec-homekit-tv/assets/19885992/98074409-9660-42d8-ad4f-5d5ea6468521" alt="me-651" width="500"/>

</div>

---

### Currently Working
- Install Directly on the Pi
- Home App (On/Off and Switching Sources)
- Read Power State and Current Input Back from TV to Update the Home App
- Finished Remote Control App Implementation

### To Do
- Finish Dockerfile
- Variable abstraction for default IP address, TV name, accessory.state file location
- There's a bug that happens if too many serial commands are sent - need to queue them up so this doesn't happen - maybe just import and use retry
- Inputs are in a random order and can't be moved

<div align="center">

<img src="https://github.com/ground7/sharp-nec-homekit-tv/assets/19885992/f941195f-2575-4a18-8d3a-374a7c56ebcb" alt="home-app" width="300"/>
<img src="https://github.com/ground7/sharp-nec-homekit-tv/assets/19885992/3c040d48-43fb-4258-a4ce-bed68a4c7a3e" alt="remote-app" width="300"/>

</div>

---

### Preinstall Steps (Doesn't work on Bookworm)

```bash
wget https://raw.githubusercontent.com/SharpNECDisplaySolutions/nec_rpi_config_tool/master/nec_rpi_config_tool.sh
chmod a+x nec_rpi_config_tool.sh
./nec_rpi_config_tool.sh
```

### Install Steps

```bash
git clone https://github.com/ground7/sharp-nec-homekit-tv.git
cd sharp-nec-homekit-tv
pip3 install -r requirements.txt
python3 tv.py
```

📍A QR code will show up in the log at this point - Scan it and add it to homekit!

### Run as Systemd Service

```bash
sudo systemctl --force --full edit homekit-tv.service
```

```s
[Unit]
Description=Advertise the pi as a HomeKit TV
After=multi-user.target

[Service]
WorkingDirectory=/home/pi/sharp-nec-homekit-tv/
User=pi
ExecStart=/usr/bin/python3 /home/pi/sharp-nec-homekit-tv/tv.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now homekit-tv.service
systemctl status homekit-tv.service
```
