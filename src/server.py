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
from random import randint
from ast import literal_eval as make_tuple

# global param
PATROL = conf.PATROL
TERMINATE_SIGNAL = False

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
    cur_dc = vertical_servo.step_move(direction = -1.0)
    logging.info("vertical dc {}".format(cur_dc))
    return "OK"
 
@app.route("/camera_down")
def camera_down():
    cur_dc = vertical_servo.step_move(direction = 1.0)
    logging.info("vertical dc {}".format(cur_dc))
    return "OK"

@app.route("/camera_left")
def camera_left():
    cur_dc = horizontal_servo.step_move(direction = 1.0)
    logging.info("horizontal dc {}".format(cur_dc))
    return "OK"
 
@app.route("/camera_right")
def camera_right():
    cur_dc = horizontal_servo.step_move(direction = -1.0)
    logging.info("horizontal dc {}".format(cur_dc))
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

@app.route("/switch_patrol")
def switch_patrol():
    global PATROL
    if PATROL == True:
        PATROL = False
    else:
        PATROL = True
    return "OK"

# https://networklore.com/start-task-with-flask/
def kicker():
    def start_loop():
        # kick off 10 times to make sure camera monitor start
        for i in range(10):
            if TERMINATE_SIGNAL: break
            sleep(2)
            logging.debug('In start loop')
            system("curl -s http://0.0.0.0:2000/video_feed | head -1 > /dev/null")
        logging.debug("Out start loop")
    t = threading.Thread(target=start_loop)
    t.start()


def patroller():
    def patrol_thread():
        pos_l = conf.PATROL_POSITION.split('|')
        cnt = 0 
        logging.debug('patrol thread start')
        pos_cnt = len(pos_l)
        while not TERMINATE_SIGNAL:
            if PATROL and pos_cnt > 1:
                pos = make_tuple(pos_l[cnt % pos_cnt])
                camera_pi.DETECT_FLG = False
                sleep(0.5)
                horizontal_servo.direct_move(pos[0], given_time = 1.0)
                vertical_servo.direct_move(pos[1], given_time = 0.5)
                camera_pi.PREVIOUS_FRAME = None
                # give camera time to adapt new vision
                sleep(2)
                camera_pi.DETECT_FLG = True
                cnt += 1
            # interval
            sleep(randint(4,7))
        logging.debug("exit patroller")
    t = threading.Thread(target=patrol_thread)
    t.start()

if __name__ == "__main__":
    try:
        FORMAT = '%(asctime)-15s|%(name)s|%(message)s'
        logging.basicConfig(filename='myapp.log', level=logging.DEBUG, format=FORMAT)

        motor_control = motor.CONTROL(RIGHT_FRONT_PIN=conf.RIGHT_FRONT_PIN, \
                                        LEFT_FRONT_PIN=conf.LEFT_FRONT_PIN, \
                                        RIGHT_BACK_PIN=conf.RIGHT_BACK_PIN, \
                                        LEFT_BACK_PIN=conf.LEFT_BACK_PIN)
        vertical_servo = servo_hw.CONTROL(PIN=conf.VERTICAL_SERVO_PIN, \
                                            STRIDE= conf.STRIDE, reset=False)
        horizontal_servo = servo_hw.CONTROL(PIN=conf.HORIZONTAL_SERVO_PIN, \
                                            STRIDE= conf.STRIDE, reset=False)
        # kick off the camera monitor thread
        kicker()
        # kick off the patroller
        patroller()
        app.run(host='0.0.0.0', port=2000, debug=False, threaded=True)

    finally:
        logging.info('\nHave a nice day ;)')
        camera_pi.TERMINATE_SIGNAL = True
        TERMINATE_SIGNAL = True

    