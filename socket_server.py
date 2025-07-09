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

    while True:
        try:
            data, site_name = receive_socket_msg(socket)
        except zmq.ZMQError as e:
            if e.errno == zmq.ETERM:
                break  # interrupted
            else:
                raise e

        try:
            print("Creating JSON packet for ", site_name)
            socketio.emit(site_name, dmap_to_json(data, site_name))
        except KeyError:
            print(f"Failed to create JSON packet for {site_name}, corrupt data fields")

if __name__ == '__main__':
    print("Starting dev server...")
    socketio.run(app, host='0.0.0.0', port=5003, debug=True)