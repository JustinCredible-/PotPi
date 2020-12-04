# PotPi

Raspberry Pi Configuration:
Enable SSH, VNC, I2C
Sudo pip install virtualenv
CD /usr/local
Sudo Mkdir PotPi
Sudo chmod 777 /usr/local/PotPi
Virtualenv PotPi
Source PotPi/bin/activate
Pip3 install adafruit-circuitpython-sht31d
Sudo Pip3 install adafruit-blinka
Pip3 install RPI.BOARD
Pip3 install influxdb
Pip3 install schedule
Pip3 install wget
Sudo cp PotPi.service /etc/systemd/system/PotPi.service and watering and timelapse
Sudo chmod 644 all service files
Sudo systemctl enable PotPi and watering and timelapse and picoffload


Computer configuration:
install Grafana and influxDB
^^ this can be done on the Pi if you're ambitious. It killed my USB stick though, too much writes I think

Probably other steps missing right now but should get you pretty close...
