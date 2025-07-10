"""
Handles receiving and processing realtime SuperDARN data from the server
"""
import datetime as dt
import dmap
import zlib
import zmq
from typing import TypedDict

# This is the data extracted from the dmap that gets
# sent to the frontend
class JsonPacket(TypedDict):
    site_name: str
    beam: int
    cp: str
    frang: int
    freq: int
    noise: int
    nrang: int
    rsep: int
    stid: int
    time: str

    elevation: list[float]
    power: list[float]
    velocity: list[float]
    width: list[float]

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
    print(f"Listening on: {address}")

    socket = zmq.Context.instance().socket(zmq.SUB)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")  # subscribe to all messages
    socket.connect(f"tcp://{address}")

    return socket

def receive_socket_msg(socket):
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

def dmap_to_json(dmap_dict: dict, site_name: str) -> JsonPacket:
    """
    Convert dmap data to json packet

    :Args:
        data (dict): Dictionary of data as returned from `dmap.read_dmap_bytes()`

    :Returns:
        JsonPacket: Dictionary representing the json packet
    """
    nrang = dmap_dict["nrang"]

    power_arr = [0.0] * nrang
    elev_arr = [0.0] * nrang
    vel_arr = [0.0] * nrang
    width_arr = [0.0] * nrang

    slist = dmap_dict["slist"]

    # Necessary?
    powers = dmap_dict["p_l"]
    for pwr, s, in zip(powers, slist):
         power_arr[s] = pwr 
    
    elevs = dmap_dict["elv"]
    for elev, s, in zip(elevs, slist):
        elev_arr[s] = elev 
    
    # TODO: Get ground scatter
    vels = dmap_dict["v"]
    for vel, s, in zip(vels, slist):
        vel_arr[s] = vel 
    
    widths = dmap_dict["w_l"]
    for width, s, in zip(widths, slist):
        width_arr[s] = width 

    return {
        "site_name": site_name,
        "beam": dmap_dict["bmnum"],
        "cp": "{0}({1})".format(convert_cp_to_text(dmap_dict["cp"]), dmap_dict["cp"]),
        "frang": dmap_dict["frang"],
        "nave": dmap_dict["nave"],
        "freq": dmap_dict["tfreq"],
        "noise": int(dmap_dict["noise.sky"]),
        "nrang": nrang,
        "rsep": dmap_dict["rsep"],
        "stid": dmap_dict["stid"],
        "time": format_dmap_date(dmap_dict),

        "elevation": elev_arr,
        "power": power_arr,
        "velocity": vel_arr,
        "width": width_arr,
        "g_scatter": dmap_dict["gflg"]
    }

def format_dmap_date(dmap_dict: dict):
    """
    Format date in dmap as a string

    :Args:
        dmap_dict (dict): The dmap dictionary
    
    :Returns:
        date (str): The date string
    """
    return dt.datetime(
            dmap_dict['time.yr'],
            dmap_dict['time.mo'],
            dmap_dict['time.dy'],
            dmap_dict['time.hr'],
            dmap_dict['time.mt'],
            dmap_dict['time.sc'],
            dmap_dict['time.us'],
            tzinfo=dt.timezone.utc,
        ).strftime('%Y-%m-%d %H:%M:%S.%f')

# Source SuperDARN Canada realtimedisplay: https://github.com/SuperDARNCanada/realtimedisplay/blob/master/realtimedisplay.py#L67
def convert_cp_to_text(cp: int):
    """
    Convert sounding mode code to a descriptive text value

    :Args:
        cp (int): The sounding mode code
    
    :Returns:
        sounding_mode (str): Type of sounding mode
    """
    return{
		-26401: "stereoscan",
		-26009: "stereoscan",
		-26008: "stereoscan",
		-26007: "stereoscan",
		-26006: "stereoscan",
		-26005: "stereoscan",
		-26004: "stereoscan",
		-26002: "stereoscan",
		-6401: "stereoscan",
		152: "stereoscan",
		153: "stereoscan",
		157: "normalsound",
		3200: "risrscan",
		3250: "twotsg",
		3251: "twotsg",
		3252: "twotsg",
		3253: "twotsg",
		3333: "ddstest",
		3370: "epopsound",
		3375: "longsound",
		3380: "politescan",
		3400: "fivepulse",
		3450: "heatsound",
		3500: "twofsound",
		3501: "twofsound",
		3520: "uafsound",
		3521: "uafsound",
		3550: "twofonebm",
		3600: "tauscan_can",
		3601: "tauscan_can",
		8510: "ltuseqscan",
		8511: "ltuseqscan",
		9211: "pcpscan",
		150:	"normalscan",
		151:	"normalscan",
		155:	"normalsound",
		3300:	"themisscan",
		200:	"rbspscan",
		3502:	"twofsound",
		3503:	"twofsound",
		-3502:	"twofsound",
		-3503:	"twofsound",
		3350:	"ulfscan",
		-3350:	"ulfscan",
		}.get(cp,"unknown")