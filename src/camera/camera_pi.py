import io
import time
import picamera
from camera.base_camera import BaseCamera
import numpy as np
import cv2
import datetime
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from RPi import GPIO
import conf
from queue import Queue
from threading import Thread
import logging
logger = logging.getLogger(__name__)

# import default CONSTANT
DATA_PATH = conf.DATA_PATH
THRESHOLD = conf.THRESHOLD
MIN_AREA = conf.MIN_AREA
SOUND_ALERT_PIN = conf.SOUND_ALERT_PIN
DETECT_FLG = conf.DETECT_FLG
SOUND_ALERT_FLG = conf.SOUND_ALERT_FLG
EMAIL_USERNAME = conf.EMAIL_USERNAME
EMAIL_FROM = conf.EMAIL_FROM
EMAIL_TO = conf.EMAIL_TO
SMTP_DOMAIN = conf.SMTP_DOMAIN
SMTP_PORT = conf.SMTP_PORT
EMAIL_PASSWORD = conf.EMAIL_PASSWORD
CAMERA_RESOLUTION = conf.CAMERA_RESOLUTION
CAMERA_ROTATION = conf.CAMERA_ROTATION
SENT_THRESHOLD = conf.SENT_THRESHOLD
DRAW_RECTANGLE = conf.DRAW_RECTANGLE
# GPIO startup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SOUND_ALERT_PIN, GPIO.OUT, initial=GPIO.HIGH)
# global argument 
TERMINATE_SIGNAL = False
SENT_CNT = 0
PREVIOUS_FRAME = None
PREVIOUS_TIMESTAMP = None
# alert queue, sharing between email sender and motion detector
ALERT_Q = Queue()

def email_sender():
    logon = False
    logger.debug("start email sender")
    logon_time = None
    global SENT_CNT
    while True:
        if SENT_CNT >= SENT_THRESHOLD or TERMINATE_SIGNAL: break
        to_be_sent = ALERT_Q.qsize()
        if to_be_sent >0 :
            logger.debug("There are {} alert imgs to be sent.".format(to_be_sent))
            file_name = ALERT_Q.get_nowait()
            try:
                if not logon:
                    try:
                        server = smtplib.SMTP_SSL(host=SMTP_DOMAIN, port=SMTP_PORT)
                        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                    except Exception as e:
                        logger.warn(e)
                        logger.warn("can't logon QQ SMTP SERVICE")
                        break
                    logon = True
                    logon_time = time.time()
                    logger.debug("login")
                # server.set_debuglevel(1) 
                msg = MIMEMultipart()
                msg['Date'] = formatdate(localtime=True)
                msg['Subject'] = "!!! Motion Detected !!! " + file_name.split(".")[0]
                # msg.attach(MIMEText("content"))
                with open(DATA_PATH + file_name, "rb") as f:
                    part = MIMEApplication(f.read(),Name=file_name)
                part['Content-Disposition'] = 'attachment; filename="%s"' % file_name
                msg.attach(part)
                server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
                SENT_CNT += 1
            except Exception as e:
                logger.warn(e)
                logger.warn(file_name + " fail, putback")
                ALERT_Q.put(file_name)
        if logon == True and ALERT_Q.empty() and time.time() - logon_time > 25 :
            server.quit()
            logon = False
            logger.debug("logout")
        time.sleep(0.3)
    logger.debug("total sent out {} emails".format(SENT_CNT))
    logger.debug("exit email sender")

# start email sender thread
T_email_sender = Thread(target=email_sender)
T_email_sender.start()

def sent_cnt_refresher():
    logger.debug("start sent_count refresher")
    global SENT_CNT
    current_day = datetime.datetime.now().strftime("%Y-%m-%d")
    while not TERMINATE_SIGNAL:
        time.sleep(10)
        if current_day != datetime.datetime.now().strftime("%Y-%m-%d"):
            SENT_CNT = 0
            current_day = datetime.datetime.now().strftime("%Y-%m-%d")
    logger.debug("exit sent_cnt refresher")

# start sent_count refresher
T_sent_cnt_refresher = Thread(target=sent_cnt_refresher)
T_sent_cnt_refresher.start()   

# https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
def detection_algorithm(frame):
    global PREVIOUS_FRAME
    global PREVIOUS_TIMESTAMP

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
 
    # if the first frame is None, initialize it
    if PREVIOUS_FRAME is None:
        PREVIOUS_FRAME = gray
        PREVIOUS_TIMESTAMP = time.time()
        detected = False
    else:
        # compute the absolute difference between the current frame and
        # first frame
        frameDelta = cv2.absdiff(PREVIOUS_FRAME, gray)
        thresh = cv2.threshold(frameDelta, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
     
        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh = cv2.dilate(thresh, None, iterations=2)
        (_,cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
     
        # loop over the contours
        label_cnt = 0
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < MIN_AREA:
                continue
            label_cnt += 1
            if DRAW_RECTANGLE:
                # compute the bounding box for the contour, draw it on the frame,
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # update the text
        if label_cnt > 0: 
            text = "Occupied"
            detected = True
            # logger.debug("detected!! {}".format(datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p")))
        else : 
            text = "Unoccupied"
            detected = False

        # draw the text and timestamp on the frame
        cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
            (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        current_timestamp = time.time()
        cv2.putText(frame, "FPS: "+str(1.0 / (current_timestamp - PREVIOUS_TIMESTAMP)),
            (frame.shape[1]-100, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        PREVIOUS_TIMESTAMP = current_timestamp
        PREVIOUS_FRAME = gray

    return frame, detected

def motion_detecter(stream):
    # https://stackoverflow.com/questions/17170752/python-opencv-load-image-from-byte-string
    ndarray = np.fromstring(stream.getvalue(), dtype=np.uint8)
    frame = cv2.imdecode(ndarray, cv2.IMREAD_COLOR)
    frame, detected  = detection_algorithm(frame)
    if detected:
        # save the frame
        # https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_gui/py_image_display/py_image_display.html#write-an-image
        file_name = "{timestamp:%Y-%m-%d-%H-%M-%S-%f}.jpg".format(
                                    timestamp=datetime.datetime.now())
        cv2.imwrite(DATA_PATH + file_name, frame)
        ALERT_Q.put(file_name)
    if SOUND_ALERT_FLG: 
        alert_control(detected)
    frame2bytes = cv2.imencode('.jpeg', frame)[1].tostring()
    return io.BytesIO(frame2bytes)

def switch_detector():
    global DETECT_FLG
    if DETECT_FLG == True:
        DETECT_FLG = False
        if SOUND_ALERT_FLG: 
            # stop alert
            alert_control(False)
    else:
        DETECT_FLG = True

def switch_alert():
    global SOUND_ALERT_FLG
    if SOUND_ALERT_FLG == True:
        SOUND_ALERT_FLG = False
    else:
        SOUND_ALERT_FLG = True

def switch_draw_rectangle():
    global DRAW_RECTANGLE
    if DRAW_RECTANGLE == True:
        DRAW_RECTANGLE = False
    else:
        DRAW_RECTANGLE = True

def set_param(thres, minarea):
    global THRESHOLD
    global MIN_AREA
    if thres is not None:
        THRESHOLD = thres
    if minarea is not None:
        MIN_AREA = minarea

def alert_control(detected):
    if detected:
        # alert
        GPIO.output(SOUND_ALERT_PIN, GPIO.LOW)
    else:
        # stop
        GPIO.output(SOUND_ALERT_PIN, GPIO.HIGH)

# https://github.com/miguelgrinberg/flask-video-streaming
class Camera(BaseCamera):
    @staticmethod
    def frames():
        with picamera.PiCamera() as camera:
            camera.resolution = CAMERA_RESOLUTION
            camera.rotation= CAMERA_ROTATION
            # let camera warm up
            time.sleep(2)

            stream = io.BytesIO()
            for _ in camera.capture_continuous(stream, 'jpeg',
                                                        use_video_port=True):
                # return current frame
                stream.seek(0)
                if DETECT_FLG:
                    stream_monitoring = motion_detecter(stream)
                    yield stream_monitoring.read()
                else:
                    yield stream.read()

                # reset stream for next frame
                stream.seek(0)
                stream.truncate()

