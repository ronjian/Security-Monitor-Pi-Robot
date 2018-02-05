import io
import time
import picamera
from .base_camera import BaseCamera
import numpy as np
import cv2
import datetime

data_path = "data/"
previous_frame = None
min_area = 500
threshold = 25

# https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
def detection_algorithm(frame):
    global previous_frame

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
 
    # if the first frame is None, initialize it
    if previous_frame is None:
        previous_frame = gray
        detected = False
    else:
        # compute the absolute difference between the current frame and
        # first frame
        frameDelta = cv2.absdiff(previous_frame, gray)
        thresh = cv2.threshold(frameDelta, threshold, 255, cv2.THRESH_BINARY)[1]
     
        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh = cv2.dilate(thresh, None, iterations=2)
        (_,cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
     
        # loop over the contours
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < min_area:
                continue
            # compute the bounding box for the contour, draw it on the frame,
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # update the text
        if len(cnts) > 0: 
            text = "Occupied"
            detected = True
            print("detected!!")
        else : 
            text = "Unoccupied"
            detected = False

        # draw the text and timestamp on the frame
        cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
            (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        previous_frame = gray

    return frame, detected

def motion_detecter(stream):
    # https://stackoverflow.com/questions/17170752/python-opencv-load-image-from-byte-string
    ndarray = np.fromstring(stream.getvalue(), dtype=np.uint8)
    frame = cv2.imdecode(ndarray, cv2.IMREAD_COLOR)
    frame, detected  = detection_algorithm(frame)
    if detected:
        # save the frame
        # https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_gui/py_image_display/py_image_display.html#write-an-image
        cv2.imwrite(data_path + "{timestamp:%H-%M-%S}.jpg".format(
                                    timestamp=datetime.datetime.now()),frame)
    frame2bytes = cv2.imencode('.jpeg', frame)[1].tostring()
    return io.BytesIO(frame2bytes)

# https://github.com/miguelgrinberg/flask-video-streaming
class Camera(BaseCamera):
    @staticmethod
    def frames():
        with picamera.PiCamera() as camera:
            camera.rotation=180
            # let camera warm up
            time.sleep(2)

            stream = io.BytesIO()
            for _ in camera.capture_continuous(stream, 'jpeg',
                                                        use_video_port=True):
                # return current frame
                stream.seek(0)
                stream_monitoring = motion_detecter(stream)
                yield stream_monitoring.read()

                # reset stream for next frame
                stream.seek(0)
                stream.truncate()

                # time.sleep(10)


