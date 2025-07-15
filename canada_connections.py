"""
Handles connection and retrieval of data from a SuperDARN Canada radar sockets which use ZMQ sockets.
"""
import zmq
import dmap
import logging
import zlib

def connect_to_zmq_socket(address: str):
    """
    Connects to `address` with a zmq.SUB connection, with all filters applied.
    Calls `handler(data)` on the received data.

    :Args:
        address: str
            formatted as hostname:port
    
    :Returns:
        dict: Dictionary of data as returned from dmap.read_dmap_bytes()
    """
    logging.info(f"Listening on: {address}")

    socket = zmq.Context.instance().socket(zmq.SUB)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")  # subscribe to all messages
    socket.connect(f"tcp://{address}")

    return socket

def receive_zmq_socket_msg(socket):
    """
    Receives message from a ZMQ socket

    :Args:
        address (str): Address formatted as hostname:port
    
    :Returns: 
        tuple[dict, str]: A tuple containing:
            - data (dict): Dictionary of data as returned from dmap.read_dmap_bytes()
            - site_name (str): Name of radar site
    """
    try:
        msg = socket.recv_multipart(copy=True) 
        site_name, compressed_bytes = msg
    except ValueError:
        raise ValueError(f"Unexpected message: {msg}")

    decompressed_msg = zlib.decompress(compressed_bytes)
    return dmap.read_dmap_bytes(decompressed_msg)[0], site_name.decode('utf-8')  # should be list[bytes] of 1 record