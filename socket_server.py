"""The socket IO server that sends the JSON packets"""
import os
import zmq
from flask import Flask
from flask_socketio import SocketIO
from process_realtime import connect_to_zmq_socket, receive_socket_msg, dmap_to_json
from dotenv import load_dotenv

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 5000

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*") #TODO: specify CORS policy?

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
            socketio.emit(site_name, dmap_to_json(data, site_name))
        except KeyError:
            print(f"Failed to create JSON packet for {site_name}, corrupt data fields")

if __name__ == '__main__':
    load_dotenv()
    socketio.run(app, host=os.getenv('HOST', DEFAULT_HOST), port=os.getenv('PORT', DEFAULT_PORT), debug=os.getenv('DEBUG', 'false') == 'true')