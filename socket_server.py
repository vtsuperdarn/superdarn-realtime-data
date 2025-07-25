"""The socket IO server that sends the JSON packets"""
import eventlet
eventlet.monkey_patch()  # Patch standard library to use eventlet

from dotenv import load_dotenv
load_dotenv()

import logging
import os
import json
import zmq
from flask import Flask
from flask_socketio import SocketIO
from process_dmap import dmap_to_json
from canada_connections import connect_to_zmq_socket, receive_zmq_socket_msg
from radar_client import RadarClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret')
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    logging.info('Client connected')

@socketio.on('disconnect')
def handle_connect():
    logging.info('Client disconnected')

def radar_listener(host, port, site_name):
    """Listens for data from a SuperDARN radar client and sends JSON packets."""
    try:
        client = RadarClient(host, port)
        logging.info(f"Connected to {site_name} at {host}:{port}")
    except Exception as e:
        logging.error(f"Failed to connect to {site_name} at {host}:{port} - {e}")
        return

    while True:
        dmap_data = client.receive_data()

        if dmap_data:
            send_json_packets(dmap_data, site_name)
        else:
            eventlet.sleep(0.1)

def zmq_listener():
    """Listens for data from SuperDARN Canada radar sockets using ZMQ."""
    socket = connect_to_zmq_socket(os.getenv('CANADA_ADDR'))

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while True:
        socks = dict(poller.poll(timeout=1000))  # timeout in milliseconds

        if socket in socks:
            ca_dmap, ca_site_name = receive_zmq_socket_msg(socket)
            if ca_dmap:
                send_json_packets(ca_dmap, ca_site_name)
        else:
            eventlet.sleep(0.1)

def send_json_packets(dmap_data: dict, site_name: str):
    """Sends JSON packets to connected clients."""
    try:
        socketio.emit(site_name, dmap_to_json(dmap_data, site_name))
        logging.info(f"Successfully created JSON packet for {site_name}")
    except KeyError as k:
        logging.warning(f"Failed to create JSON packet for {site_name}, missing data field: {k}")

def start_listeners():
    """Starts the radar listeners for each configured radar."""
    logging.info("Starting radar listeners...")

    # Load the radar configuration from radars.config.json
    try:
        radars_config = json.load(open('radars.config.json'))
    except Exception as e:
        logging.error(f"Failed to load radar configuration: {e}")
        return

    for site_name, config in radars_config.items():
        host = config.get('host')
        port = config.get('port')

        if not host or not port:
            logging.warning(f"Skipping {site_name}, missing host or port in configuration.")
            continue

        socketio.start_background_task(radar_listener, host, port, site_name)

    # Start the ZMQ listener for Canada radars
    socketio.start_background_task(zmq_listener)

start_listeners()

if __name__ == '__main__':
    logging.info("Starting dev server...")
    socketio.run(app, host='0.0.0.0', port=5003, debug=True)