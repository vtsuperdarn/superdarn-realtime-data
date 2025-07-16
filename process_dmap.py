"""
Proccesses DMAP as JSON packets for the frontend.
"""
import datetime as dt
import logging
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
    g_scatter_arr = [0] * nrang

    if "slist" in dmap_dict:
        slist = dmap_dict["slist"]

        for pwr, s, in zip(dmap_dict["p_l"], slist):
            power_arr[s] = float(pwr) 
        
        for elev, s, in zip(dmap_dict["elv"], slist):
            elev_arr[s] = float(elev) 
        
        for vel, s, in zip(dmap_dict["v"], slist):
            vel_arr[s] = float(vel) 

        for g_scatter, s, in zip(dmap_dict["gflg"], slist):
            g_scatter_arr[s] = int(g_scatter)

        for width, s, in zip(dmap_dict["w_l"], slist):
            width_arr[s] = float(width)
    else:
        # Some packets do not have slist. Why?
        logging.warning(f"Missing slist in dmap data for {site_name}") 

    return {
        "site_name": site_name,
        "beam": int(dmap_dict["bmnum"]),
        "cp": "{0}({1})".format(convert_cp_to_text(dmap_dict["cp"]), dmap_dict["cp"]),
        "frang": int(dmap_dict["frang"]),
        "nave": int(dmap_dict["nave"]),
        "freq": int(dmap_dict["tfreq"]),
        "noise": int(dmap_dict["noise.sky"]),
        "nrang": nrang,
        "rsep": int(dmap_dict["rsep"]),
        "stid": int(dmap_dict["stid"]),
        "scan": int(dmap_dict["scan"]),
        "gflg": dmap_dict["gflg"].tolist(),
        "v": dmap_dict["v"].tolist(),
        "time": format_dmap_date(dmap_dict),

        "elevation": elev_arr,
        "power": power_arr,
        "velocity": vel_arr,
        "width": width_arr,
        "g_scatter": g_scatter_arr
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