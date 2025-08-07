"""The socket IO server that sends the JSON packets"""
import eventlet
eventlet.monkey_patch()  # Patch standard library to use eventlet

import logging
import os
import json
import zmq
import traceback
import datetime as dt
from .data_processing.process_dmap import dmap_to_json
from .radar_connections.canada_zmq_connections import connect_to_zmq_socket, receive_zmq_socket_msg
from .radar_connections.radar_socket_client import RadarSocketClient
from .data_processing.process_echoes import write_echo_counts


def start_socketio_listeners(socketio, app):
    """Starts the radar listeners for each configured radar."""
    logging.info("Starting radar listeners...")

    # Load the radar configuration from radars.config.json
    try:
        radars_config = json.load(open('radars.config.json'))
    except Exception as e:
        logging.error(
            f"Failed to load radar configuration:\n{traceback.format_exc()}")
        return

    for site_name, config in radars_config.items():
        host = config.get('host')
        port = config.get('port')

        if not host or not port:
            logging.warning(
                f"Skipping {site_name}, missing host or port in configuration.")
            continue

        socketio.start_background_task(
            radar_listener, socketio, app, host, port, site_name)

    # Start the ZMQ listener for Canada radars
    socketio.start_background_task(zmq_listener, socketio, app)


def radar_listener(socketio, app, host, port, site_name):
    """Listens for data from a SuperDARN radar client and sends JSON packets."""
    try:
        client = RadarSocketClient(host, port)
        logging.info(f"Connected to {site_name} at {host}:{port}")
    except Exception as e:
        logging.error(
            f"Failed to connect to {site_name} at '{host}:{port}':\n{traceback.format_exc()}")
        return

    while True:
        try:
            dmap_data = client.receive_data()

            if dmap_data:
                with app.app_context():
                    send_data(socketio, dmap_data, site_name)
            else:
                eventlet.sleep(0.1)
        except Exception as e:
            logging.error(
                f"Error receiving data from {site_name} at '{host}:{port}':\n{traceback.format_exc()}")
            eventlet.sleep(0.1)


def zmq_listener(socketio, app):
    """Listens for data from SuperDARN Canada radar sockets using ZMQ."""
    socket = connect_to_zmq_socket(os.getenv('CANADA_ADDR'))

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while True:
        try:
            socks = dict(poller.poll(timeout=1000))  # timeout in milliseconds

            if socket in socks:
                ca_dmap, ca_site_name = receive_zmq_socket_msg(socket)
                if ca_dmap:
                    with app.app_context():
                        send_data(socketio, ca_dmap, ca_site_name)
            else:
                eventlet.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in ZMQ listener:\n{traceback.format_exc()}")
            eventlet.sleep(0.1)


def send_data(socketio, dmap_dict: dict, site_name: str):
    """Send all radar data to connected clients."""
    send_json_packets(socketio, dmap_dict, site_name)
    send_and_write_echo_counts(socketio, dmap_dict, site_name)


def send_and_write_echo_counts(socketio, dmap_dict: dict, site_name: str):
    """Send echo counts (if a complete scan) and write to database"""
    echo_counts = write_echo_counts(dmap_dict, site_name)

    if echo_counts:
        timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            socketio.emit(f"{site_name}/echoes", {
                "total_echoes": echo_counts[0], "ionospheric_echoes": echo_counts[1], "ground_scatter_echoes": echo_counts[2], "timestamp": timestamp})
            logging.info(f"Successfully sent echoes for {site_name}")
        except Exception as e:
            logging.error(
                f"Failed to send echoes for {site_name} due to error:\n{traceback.format_exc()}")


def send_json_packets(socketio, dmap_data: dict, site_name: str):
    """Sends JSON packets to connected clients."""
    try:
        socketio.emit(site_name, dmap_to_json(dmap_data, site_name))
        logging.info(f"Successfully created JSON packet for {site_name}")
    except KeyError as k:
        logging.warning(
            f"Failed to create JSON packet for {site_name}, missing data field: {k}")
