from flask import Flask, render_template, request, Response
from pimodules import motor, servo_hw
from camera import camera_pi


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


if __name__ == "__main__":
    try:
        STRIDE = 0.02
        motor_control = motor.CONTROL(RIGHT_FRONT_PIN=17, \
                                        LEFT_FRONT_PIN=23, \
                                        RIGHT_BACK_PIN=22, \
                                        LEFT_BACK_PIN=24)
        vertical_servo = servo_hw.CONTROL(PIN=26, STRIDE= STRIDE, reset=False)
        horizontal_servo = servo_hw.CONTROL(PIN=19, STRIDE= STRIDE, reset=False)
        app.run(host='0.0.0.0', port=2000, debug=False, threaded=True)
    finally:
        print('\nHave a nice day ;)')

    