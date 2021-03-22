import eventlet
eventlet.monkey_patch()

from flask import Flask, Response,render_template
from flask_socketio import SocketIO, send, emit
from subprocess import Popen, call

import time
import board
import busio
import adafruit_mpu6050
import json
import socket

import signal
import sys
from queue import Queue


import digitalio
from PIL import Image, ImageDraw
import adafruit_rgb_display.ili9341 as ili9341
import adafruit_rgb_display.st7789 as st7789  # pylint: disable=unused-import
import adafruit_rgb_display.hx8357 as hx8357  # pylint: disable=unused-import
import adafruit_rgb_display.st7735 as st7735  # pylint: disable=unused-import
import adafruit_rgb_display.ssd1351 as ssd1351  # pylint: disable=unused-import
import adafruit_rgb_display.ssd1331 as ssd1331  # pylint: disable=unused-import


import pup
 
i2c = busio.I2C(board.SCL, board.SDA)
mpu = adafruit_mpu6050.MPU6050(i2c)


# Configuration for CS and DC pins (these are PiTFT defaults):
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 24000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

# SETUP FLASK

hostname = socket.gethostname()
hardware = 'plughw:2,0'

app = Flask(__name__)
socketio = SocketIO(app)
audio_stream = Popen("/usr/bin/cvlc alsa://"+hardware+" --sout='#transcode{vcodec=none,acodec=mp3,ab=256,channels=2,samplerate=44100,scodec=none}:http{mux=mp3,dst=:8080/}' --no-sout-all --sout-keep", shell=True)

# BLANK SCREEN

# Create blank image for drawing.
# Make sure to create image with mode 'RGB' for full color.
if disp.rotation % 180 == 90:
    height = disp.width  # we swap height/width to rotate it to landscape!
    width = disp.height
else:
    width = disp.width  # we swap height/width to rotate it to landscape!
    height = disp.height
image = Image.new("RGB", (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
disp.image(image)


def diplay_img(image):
    backlight = digitalio.DigitalInOut(board.D22)
    backlight.switch_to_output()
    backlight.value = True

    # Scale the image to the smaller screen dimension
    image_ratio = image.width / image.height
    screen_ratio = width / height
    if screen_ratio < image_ratio:
        scaled_width = image.width * height // image.height
        scaled_height = height
    else:
        scaled_width = width
        scaled_height = image.height * width // image.width
    image = image.resize((scaled_width, scaled_height), Image.BICUBIC)

    # Crop and center the image
    x = scaled_width // 2 - width // 2
    y = scaled_height // 2 - height // 2
    image = image.crop((x, y, x + width, y + height))

    # Display image.
    disp.image(image)

frames2play = pup.FRAMES['walk_right']

# def play_sequence(action, loop=True):
#     frames = pup.FRAMES[action]
#     while True:
#         for frame in frames:
#             diplay_img(frame)
#             time.sleep(0.1)
#         if not loop:
#             break

# WIZARD INTERACTIONS

@socketio.on('walk_front')
def handle_walk_front():
    frames2play = pup.FRAMES['walk_front']*60
    # play_sequence('walk_front')

@socketio.on('walk_right')
def handle_walk_right():
    frames2play = pup.FRAMES['walk_right']*60
    # play_sequence('walk_right')

@socketio.on('walk_back')
def handle_walk_back():
    frames2play = pup.FRAMES['walk_back']*60
    # play_sequence('walk_back')

@socketio.on('walk_left')
def handle_walk_left():
    frames2play = pup.FRAMES['walk_left']*60
    # play_sequence('walk_left')

@socketio.on('sit_front')
def handle_sit_front():
    frames2play = pup.FRAMES['sit_front']*60
    # play_sequence('sit_front', loop=False)

@socketio.on('sit_side')
def handle_sit_side():
    frames2play = pup.FRAMES['sit_side']
    # play_sequence('sit_side', loop=False)
    frames2play = pup.FRAMES['sitting_side']*60
    # play_sequence('sitting_side')

@socketio.on('down_side')
def handle_down_side():
    frames2play = pup.FRAMES['down_side']*60
    # play_sequence('down_side')

@socketio.on('run_side')
def handle_run_side():
    frames2play = pup.FRAMES['run_side']*60
    # play_sequence('run_side')


@socketio.on('bark')
def handle_bark():
    call("echo 'woof woof' | festival --tts", shell=True)

@socketio.on('speak')
def handle_speak(val):
    call(f"echo '{val}' | festival --tts", shell=True)

@socketio.on('connect')
def test_connect():
    print('connected')
    emit('after connect',  {'data':'Lets dance'})

@socketio.on('ping-gps')
def handle_message(val):
    # print(mpu.acceleration)
    emit('pong-gps', mpu.acceleration)

@socketio.on('ping-tft')
def handle_tft():
    if len(frames2play>1):
        diplay_img(frames2play.pop())
    else:
        diplay_img(frames2play[0])

@app.route('/')
def index():
    return render_template('index.html', hostname=hostname)

def signal_handler(sig, frame):
    print('Closing Gracefully')
    audio_stream.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)


