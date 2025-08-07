"""
Manages the reading of raw (bytes) data packets into a DMAP dict from a SuperDARN radar socket.
"""
import socket
import dmap
import logging
import traceback

PACKET_SIZE = 8  # Size of the packet header
ENCODING_IDENTIFIER = [73, 8, 30, 0]  # Encoding identifier for dmap files

class RadarSocketClient:
    """
    Handles the connection and data retrieval from a SuperDARN radar client.
    """
    def __init__(self, host: str, port: int, timeout: float = 20.0):
        """
        Initializes the RadarClient with the given host and port.

        :Args:
            host (str): The hostname or IP address of the radar server.
            port (int): The port number to connect to.
        """
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(timeout)  # Set a timeout for blocking socket operations
        self.client_socket.connect((host, port))
        self.host = host
        self.port = port
        self.timeout = timeout
        # Keep track of invalid packets received
        self._invalid_packet_count = 0

    def __del__(self):
        """Ensures the client socket is closed when the object is deleted."""
        self.client_socket.close()

    def receive_data(self) -> dict | None:
        """
        Receives and processes data packets from the radar server.

        :Returns:
            dict | None: Returns the dmap data as a dictionary if successful, otherwise None.
        """
        if self._invalid_packet_count > 10:
            logging.warning(f"Too many invalid packets received from {self.host}:{self.port}, reconnecting...")
            self.reconnect()
            self._invalid_packet_count = 0

        try:
            packet = self.client_socket.recv(PACKET_SIZE)
        except socket.timeout:
            logging.warning(f"Socket timeout on {self.host}:{self.port}, attempting to reconnect...")
            self.reconnect()
            return None
        except Exception as e:
            logging.error(f"Socket error on {self.host}:{self.port}: {e}, attempting to reconnect...")
            self.reconnect()
            return None

        if not packet:
            logging.debug(f"Connection on {self.host}:{self.port} sending empty packets")
            self._invalid_packet_count += 1
            return None

        if not verify_packet_encoding(packet):
            logging.debug(f"Received invalid packet from {self.host}:{self.port}")
            self._invalid_packet_count += 1
            # Not a dmap packet, skip processing
            return None

        # Next 4 bytes represent the length of the data
        block_size = int.from_bytes(packet[4:8], byteorder='little')

        # If the block size is invalid, skip processing
        if block_size <= 0 or block_size > 10000:
            logging.debug("Invalid data length of {0}".format(block_size))
            return None

        raw_data = read_data_block(self.client_socket, block_size)

        try:
            return dmap.read_dmap_bytes(raw_data)[0]
        except Exception as e:
            logging.error(f"Error reading dmap data:\n{traceback.format_exc()}")
            return None

    def reconnect(self):
        try:
            self.client_socket.close()
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(self.timeout)
            self.client_socket.connect((self.host, self.port))
        except Exception as e:
            logging.error(f"Failed to reconnect to {self.host}:{self.port}:\n{traceback.format_exc()}")
        

def verify_packet_encoding(packet: bytes) -> bool:
    """
    Verifies if a packet received from a socket is a dmap file based on the
    [encoding identifier](https://radar-software-toolkit-rst.readthedocs.io/en/latest/references/general/dmap_data/#block-format).

    :Args:
        packet (bytes): The raw packet data.

    :Returns:
        bool: True if the packet is valid, False otherwise.
    """
    if not packet or len(packet) < PACKET_SIZE:
        return False
    
    header = list(packet[:4])

    return header == ENCODING_IDENTIFIER

def read_data_block(client_socket: socket.socket, block_size: int) -> bytes:
    """
    Reads a block of data from the radar socket.

    :Args:
        client_socket (socket.socket): The socket connected to the radar server.
        block_size (int): The size of the block to read.

    :Returns:
        bytes: The raw data read from the socket.
    """
    data = b''
    byte_counter = block_size

    while len(data) < block_size:
        rec_data = client_socket.recv(byte_counter)
        data += rec_data
        byte_counter -= len(rec_data)

    return data