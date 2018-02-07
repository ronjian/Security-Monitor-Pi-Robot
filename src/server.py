#!/usr/bin/python3
from flask import Flask, render_template, request, Response
from pimodules import motor, servo_hw
from camera import camera_pi
from os import listdir,remove, system
import conf
import sys
import threading
from time import sleep
import logging


app = Flask(__name__)


@app.route("/")
def index():
    return render_template('index.html')

def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(camera_pi.Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/forward")
def forward():
    speed_pct = int(request.args.get('speed_pct'))
    motor_control.backward(speed_pct)
    return "OK"
 
@app.route("/backward")
def backward():
    speed_pct = int(request.args.get('speed_pct'))
    motor_control.forward(speed_pct)
    return "OK"

@app.route("/turn_left")
def turn_left():
    speed_pct = int(request.args.get('speed_pct'))
    motor_control.left(speed_pct)
    return "OK"
 
@app.route("/turn_right")
def turn_right():
    speed_pct = int(request.args.get('speed_pct'))
    motor_control.right(speed_pct)
    return "OK"

@app.route("/stop")
def stop():
    motor_control.stop()
    return "OK"

@app.route("/camera_up")
def camera_up():
    vertical_servo.step_move(direction = -1.0)
    return "OK"
 
@app.route("/camera_down")
def camera_down():
    vertical_servo.step_move(direction = 1.0)
    return "OK"

@app.route("/camera_left")
def camera_left():
    horizontal_servo.step_move(direction = 1.0)
    return "OK"
 
@app.route("/camera_right")
def camera_right():
    horizontal_servo.step_move(direction = -1.0)
    return "OK"

@app.route("/camera_reset")
def camera_reset():
    vertical_servo.reset()
    horizontal_servo.reset()
    return "OK"

@app.route("/switch_detector")
def switch_detector():
    camera_pi.switch_detector()
    return "OK"

@app.route("/switch_alert")
def switch_alert():
    camera_pi.switch_alert()
    return "OK"

@app.route("/switch_draw_rectangle")
def switch_draw_rectangle():
    camera_pi.switch_draw_rectangle()
    return "OK"

@app.route("/set_param")
def set_param():
    thres = int(request.args.get('thres'))
    minarea = int(request.args.get('minarea'))
    camera_pi.set_param(thres, minarea)
    return "OK"

# https://networklore.com/start-task-with-flask/
def kicker():
    def start_loop():
        # kick off 10 times to make sure camera monitor start
        for i in range(10):
            sleep(2)
            logging.debug('In start loop')
            system("curl -s http://0.0.0.0:2000/video_feed | head -1 > /dev/null")
        logging.debug("Out start loop")
    thread = threading.Thread(target=start_loop)
    thread.start()


if __name__ == "__main__":
    try:
        
        logging.basicConfig(filename='myapp.log', level=logging.DEBUG)

        motor_control = motor.CONTROL(RIGHT_FRONT_PIN=conf.RIGHT_FRONT_PIN, \
                                        LEFT_FRONT_PIN=conf.LEFT_FRONT_PIN, \
                                        RIGHT_BACK_PIN=conf.RIGHT_BACK_PIN, \
                                        LEFT_BACK_PIN=conf.LEFT_BACK_PIN)
        vertical_servo = servo_hw.CONTROL(PIN=conf.VERTICAL_SERVO_PIN, \
                                            STRIDE= conf.STRIDE, reset=False)
        horizontal_servo = servo_hw.CONTROL(PIN=conf.HORIZONTAL_SERVO_PIN, \
                                            STRIDE= conf.STRIDE, reset=False)
        # kick the camera monitor thread
        kicker()
        app.run(host='0.0.0.0', port=2000, debug=False, threaded=True)

    finally:
        logging.info('\nHave a nice day ;)')
        camera_pi.TERMINATE_SIGNAL = True

    