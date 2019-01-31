#!/usr/bin/python3
from flask import Flask, render_template, request, Response, url_for, redirect, flash
from pimodules import motor, servo_hw
from camera import camera_pi
from os import listdir,remove, system
import conf
import sys, os
from threading import Thread
from time import sleep, time
import logging
from random import randint
from ast import literal_eval as make_tuple
import datetime
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import shutil


# global params
PATROL = conf.PATROL
SENT_CNT = 0
TERMINATE_SIGNAL = False
VERTICAL_DC = 1500
HORIZONTAL_DC = 1500

app = Flask(__name__)
app.secret_key = 'some_secret'

@app.route("/")
def welcome():
    return render_template('welcome.html')

@app.route("/asljflasdjfasdfwl")
def asljflasdjfasdfwl():
    return render_template('asljflasdjfasdfwl.html')

# credit: http://docs.jinkan.org/docs/flask/patterns/flashing.html
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'rong' or \
                request.form['password'] != '64573635':
            error = 'Invalid credentials'
        else:
            flash('You were successfully logged in')
            return redirect(url_for('asljflasdjfasdfwl'))
    return render_template('login.html', error=error)

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
    global VERTICAL_DC
    VERTICAL_DC = vertical_servo.step_move(direction = -1.0)
    logging.info("vertical dc {}".format(VERTICAL_DC))
    return "OK"
 
@app.route("/camera_down")
def camera_down():
    global VERTICAL_DC
    VERTICAL_DC = vertical_servo.step_move(direction = 1.0)
    logging.info("vertical dc {}".format(VERTICAL_DC))
    return "OK"

@app.route("/camera_left")
def camera_left():
    global HORIZONTAL_DC
    HORIZONTAL_DC = horizontal_servo.step_move(direction = 1.0)
    logging.info("horizontal dc {}".format(HORIZONTAL_DC))
    return "OK"
 
@app.route("/camera_right")
def camera_right():
    global HORIZONTAL_DC
    HORIZONTAL_DC = horizontal_servo.step_move(direction = -1.0)
    logging.info("horizontal dc {}".format(HORIZONTAL_DC))
    return "OK"

@app.route("/camera_capture")
def camera_capture():
    camera_pi.CAPTURE=True
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

@app.route("/pos_clear")
def pos_clear():
    conf.PATROL_POSITION=None
    return "OK"

@app.route("/pos_add")
def pos_add():
    if conf.PATROL_POSITION is None:
        conf.PATROL_POSITION = "(" + str(HORIZONTAL_DC) + ", " + str(VERTICAL_DC) + ")"
    else:
        conf.PATROL_POSITION += "|(" + str(HORIZONTAL_DC) + ", " + str(VERTICAL_DC) + ")"
    return "OK"

@app.route("/pos_set")
def pos_set():
    logger = logging.getLogger("patrol position setter")
    conf.set_config(sec="DEFAULT", k="PATROL_POSITION", v=conf.PATROL_POSITION)
    logger.debug("It's going to demo twice")
    for i in range(2):
        for pos in conf.PATROL_POSITION.split('|'):
            pos = make_tuple(pos)
            horizontal_servo.direct_move(pos[0], given_time = 0.6)
            vertical_servo.direct_move(pos[1], given_time = 0.3)
            sleep(1)
    return "OK"

# https://networklore.com/start-task-with-flask/
def start_looper():
    def start_loop():
        logger = logging.getLogger("start_looper")
        # kick off 10 times to make sure camera monitor start
        for i in range(10):
            if TERMINATE_SIGNAL: break
            sleep(2)
            logger.debug('In start loop')
            system("curl -s http://0.0.0.0:2000/video_feed | head -1 > /dev/null")
        logger.debug("Out start loop")
    t = Thread(target=start_loop)
    t.start()

def patroller():
    def patrol_thread():
        logger = logging.getLogger("patroller")
        cnt = 0 
        logger.debug('patrol thread start')
        # patrol interval
        f, t = make_tuple(conf.PATROL_INTERVAL)
        while not TERMINATE_SIGNAL and PATROL:
            pos_l = conf.PATROL_POSITION.split('|')
            pos_cnt = len(pos_l)
            pos = make_tuple(pos_l[cnt % pos_cnt])
            camera_pi.DETECT_FLG = False
            horizontal_servo.direct_move(pos[0], given_time = 0.6)
            vertical_servo.direct_move(pos[1], given_time = 0.3)
            # give camera time to adapt new vision
            #sleep(0.3)
            camera_pi.PREVIOUS_FRAME = None
            camera_pi.DETECT_FLG = True
            cnt += 1
            sleep(randint(f,t))
            while camera_pi.PERSON_FLG:
                logger.debug("person detected, patroller is waiting")
                sleep(randint(f,t))
        logger.debug("exit patroller")
    t = Thread(target=patrol_thread)
    t.start()

def email_sender():
    def email_sender_thread():
        logger = logging.getLogger("email_sender")
        logon = False
        logger.debug("start email sender")
        logon_time = None
        global SENT_CNT
        while True:
            if TERMINATE_SIGNAL: break
            # check if need to logout
            if logon == True and time() - logon_time > 30 :
                server.quit()
                logon = False
                logger.debug("logout")
            # there is a threshold make sure this process will 
            # not become auto spam email machine
            if SENT_CNT >= conf.SENT_THRESHOLD: 
                sleep(10)
                continue
            to_be_sent = camera_pi.ALERT_Q.qsize()
            if to_be_sent >0 :
                logger.debug("There are {} alert imgs to be sent.".format(to_be_sent))
                file_name = camera_pi.ALERT_Q.get_nowait()
                try:
                    if not logon:
                        try:
                            server = smtplib.SMTP_SSL(host=conf.SMTP_DOMAIN, \
                                                        port=conf.SMTP_PORT)
                            server.login(conf.EMAIL_USERNAME, conf.EMAIL_PASSWORD)
                        except Exception as e:
                            logger.warn(e)
                            logger.warn("can't logon QQ SMTP SERVICE")
                            sleep(5)
                            continue
                        logon = True
                        logon_time =time()
                        logger.debug("login")
                    # server.set_debuglevel(1) 
                    msg = MIMEMultipart()
                    msg['Date'] = formatdate(localtime=True)
                    msg['Subject'] = "!!! Motion Detected !!! " + file_name.split(".")[0]
                    # msg.attach(MIMEText("content"))
                    with open(conf.DATA_PATH + file_name, "rb") as f:
                        part = MIMEApplication(f.read(),Name=file_name)
                    part['Content-Disposition'] = 'attachment; filename="%s"' % file_name
                    msg.attach(part)
                    server.sendmail(conf.EMAIL_FROM, conf.EMAIL_TO, msg.as_string())
                    SENT_CNT += 1
                except Exception as e:
                    logger.warn(e)
                    logger.warn(file_name + " fail, putback")
                    camera_pi.ALERT_Q.put(file_name)

            sleep(0.3)
        logger.debug("total sent out {} emails".format(SENT_CNT))
        logger.debug("exit email sender")

    # start email sender thread
    t = Thread(target=email_sender_thread)
    t.start()

def sent_cnt_refresher():
    def sent_cnt_refresher_thread():
        logger = logging.getLogger("sent_cnt_refresher")
        logger.debug("start sent_count refresher")
        global SENT_CNT
        current_day = datetime.datetime.now().strftime("%Y-%m-%d")
        while not TERMINATE_SIGNAL:
            sleep(10)
            if current_day != datetime.datetime.now().strftime("%Y-%m-%d"):
                logger.debug("cleaning alert queue")
                while not camera_pi.ALERT_Q.empty():
                    _ = camera_pi.ALERT_Q.get_nowait()
                logger.debug("alert queue is cleaned")
                SENT_CNT = 0
                current_day = datetime.datetime.now().strftime("%Y-%m-%d")
                shutil.rmtree("data/")
                os.makedirs("data/")
                logger.debug("data dir is cleaned")
        logger.debug("exit sent_cnt refresher")

    # start sent_count refresher
    t = Thread(target=sent_cnt_refresher_thread)
    t.start()   

def recreate_dir(path):
    """recreate dir: if exists, then purge, if not, then create"""
    print("re-create directory: ", path)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


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
        # kick off threads
        start_looper()
        patroller()
        email_sender()
        sent_cnt_refresher()
        # clear data dir
        recreate_dir("data/")
        app.run(host='0.0.0.0', port=2000, debug=False, threaded=True)

    finally:
        # signal to stop all threads
        logging.info("send the signal to stop all threads")
        TERMINATE_SIGNAL = True
        logging.info('\nHave a nice day ;)')

    