from flask import Flask, render_template, Response
import cv2
import numpy as np
from pyngrok import ngrok
import pyscreenshot
from werkzeug.serving import make_server
import threading
import time
import requests

import base64
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

camera = cv2.VideoCapture(0)

cam_on = False
count = 0



@socketio.on("video")
def gen_frames():
    """
    Generates video frames from the camera and emits them via socket.

    Emits:
        video: The base64 encoded image frame.
    """
    global cam_on, camera
    success, frame = camera.read()

    if (not success) or (not cam_on):
        camera.release()
        camera = cv2.VideoCapture(0)
    else:
        ret, frame_buffer = cv2.imencode('.jpg', frame)
        frame = frame_buffer.tobytes()
        emit('video', {'image': base64.b64encode(frame).decode('utf-8')}, broadcast=True)

@socketio.on('screen')
def generateScreenFrames():
    """
    Captures the screen and emits the frames via socket.

    Emits:
        screen: The base64 encoded screen frame.
    """
    img = pyscreenshot.grab()
    ret, frame_buffer = cv2.imencode('.png', cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB))
    frame = frame_buffer.tobytes()
    emit('screen', {'image': base64.b64encode(frame).decode('utf-8')}, broadcast=True)

@app.route('/screen')
def screenPage():
    """
    Renders the screen streaming page.

    Returns:
        str: The rendered HTML template for screen streaming.
    """
    return render_template('screen.html')

@app.route('/')
def index():
    """
    Renders the video streaming home page.

    Returns:
        str: The rendered HTML template for the home page.
    """
    return render_template('index.html')

@socketio.on('cconnect')
def connect():
    """
    Handles socket connection event, turning on the camera.
    """
    global cam_on, count
    cam_on = True
    count += 1

@socketio.on('disconnect')
def disconnect():
    """
    Handles socket disconnection event, turning off the camera if no clients are connected.
    """
    global count
    count -= 1
    if count < 0:
        count = 0
    if count == 0:
        global cam_on, camera
        camera = cv2.VideoCapture(0)
        cam_on = False


@app.route('/stop')
def stop():
    """
    Stops the socket server.

    Returns:
        str: Confirmation message of server stop.
    """
    socketio.stop()
    return 'stopped'

def start_server():
    """
    Starts the Flask socket server.
    """
    global socketio
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)

def start_server_in_thread():
    """
    Starts the server in a separate thread.
    """
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    print('server started')


def stop_server():
    """
    Stops the server by sending a stop request.
    """
    global socketio
    try:
        data = requests.get('http://localhost:5000/stop')
        print(data.text)
    except:
        print('server not running')

if __name__ == "__main__":
    pass
