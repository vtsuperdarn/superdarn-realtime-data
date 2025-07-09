"""The socket IO server that sends the JSON packets"""
import eventlet
eventlet.monkey_patch()  # Patch standard library to use eventlet

from dotenv import load_dotenv
load_dotenv()

import os
import zmq
from flask import Flask
from flask_socketio import SocketIO
from process_realtime import connect_to_zmq_socket, receive_socket_msg, dmap_to_json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret')
socketio = SocketIO(app, cors_allowed_origins="*") 

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    socketio.start_background_task(start_listening)

def start_listening():
    socket = connect_to_zmq_socket(os.getenv('CANADA_ADDR'))

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while True:
        socks = dict(poller.poll(timeout=1000))  # timeout in milliseconds

        if socket in socks:
            try:
                data, site_name = receive_socket_msg(socket)
                print("Creating JSON packet for ", site_name)
                socketio.emit(site_name, dmap_to_json(data, site_name))
            except KeyError:
                print(f"Failed to create JSON packet for {site_name}, corrupt data fields")
        else:
            # No message yet — yield control so Socket.IO can send heartbeats
            eventlet.sleep(0.1)

if __name__ == '__main__':
    print("Starting dev server...")
    socketio.run(app, host='0.0.0.0', port=5003, debug=True)