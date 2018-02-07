import configparser

# Constant configure
# credit: https://docs.python.org/3/library/configparser.html#supported-datatypes
config = configparser.ConfigParser()
import os
print(os.path.abspath('./conf.ini'))
config.read('./conf.ini')
DATA_PATH = config['DEFAULT']['DATA_PATH'] 
THRESHOLD = int(config['DEFAULT']['THRESHOLD']) 
MIN_AREA = int(config['DEFAULT']['MIN_AREA']) 
SOUND_ALERT_PIN = int(config['DEFAULT']['SOUND_ALERT_PIN'])
DETECT_FLG = config['DEFAULT'].getboolean('DETECT_FLG') 
SOUND_ALERT_FLG = config['DEFAULT'].getboolean('SOUND_ALERT_FLG') 
EMAIL_USERNAME = config['DEFAULT']['EMAIL_USERNAME']
EMAIL_FROM = config['DEFAULT']['EMAIL_FROM']
EMAIL_TO = config['DEFAULT']['EMAIL_TO']
SMTP_DOMAIN = config['DEFAULT']['SMTP_DOMAIN']
SMTP_PORT = int(config['DEFAULT']['SMTP_PORT'])
with open("password.txt", 'rb') as f:
    EMAIL_PASSWORD = str(f.read(), 'utf-8')
CAMERA_RESOLUTION = config['DEFAULT']['CAMERA_RESOLUTION']
CAMERA_ROTATION = int(config['DEFAULT']['CAMERA_ROTATION'])
VERTICAL_SERVO_PIN = int(config['DEFAULT']['VERTICAL_SERVO_PIN'])
HORIZONTAL_SERVO_PIN = int(config['DEFAULT']['HORIZONTAL_SERVO_PIN'])
STRIDE = float(config['DEFAULT']['STRIDE'])
RIGHT_FRONT_PIN=int(config['DEFAULT']['RIGHT_FRONT_PIN'])
LEFT_FRONT_PIN=int(config['DEFAULT']['LEFT_FRONT_PIN'])
RIGHT_BACK_PIN=int(config['DEFAULT']['RIGHT_BACK_PIN'])
LEFT_BACK_PIN=int(config['DEFAULT']['LEFT_BACK_PIN'])
