
# setup steps:
- ```sudo raspi-config``` to enable camera and reboot Pi
- If you unfortunately delete the camera corresponding firmware like me, don't worry and check this [post](https://raspberrypi.stackexchange.com/questions/67156/how-can-i-install-raspistill-raspicam-on-a-distro-that-doesnt-include-them) to restore it. It took me 20 mins to restore Pi camera firmware.
- Verify the camera setup as ```raspistill -v -o test.jpg```, you may check the [official docs](https://www.raspberrypi.org/documentation/raspbian/applications/camera.md) for detail.

This project is built on Python3, dependency packages as below:
- install [picamera ](https://picamera.readthedocs.io/en/release-1.13/) module
- install [opencv](https://www.pyimagesearch.com/2017/09/04/raspbian-stretch-install-opencv-3-python-on-your-raspberry-pi/)
- install [flask](http://flask.pocoo.org/)
- install [RPi.GPIO](https://sourceforge.net/p/raspberry-gpio-python/wiki/install/)
- install [pigpio](http://abyz.me.uk/rpi/pigpio/download.html)
- install [pimodules](https://github.com/ronjian/pimodules)

# Start server:
```
python3 src/server.py
```

Open url ```http://192.168.1.110:2000/```(replace with your Pi IP address) in your browser.  



