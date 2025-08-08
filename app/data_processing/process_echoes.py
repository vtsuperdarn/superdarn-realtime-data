import logging
import datetime as dt
import pandas as pd
from collections import defaultdict

from ..models import EchoCounts, db


# Buffer for accumulating echo counts per site
echo_buffer = defaultdict(lambda: {
    'total_echoes': 0,
    'ionospheric_echoes': 0,
    'ground_scatter_echoes': 0,
    'count': 0,
    'last_timestamp': None
})

def write_echo_counts(dmap_dict: dict, site_name: str) -> tuple[int, int, int] | None:
    """
    Buffer and average echo counts per scan, then write to the database when a scan completes.

    Returns the average total echoes, average ionospheric echoes, and average ground scatter echoes after a complete scan.
    If the scan hasn't been completed, returns None
    """
    try:
        num_echoes, num_ionosph_echoes, num_grd_sctr_echoes = get_num_echoes(dmap_dict)
    except KeyError as e:
        logging.debug(f"Failed to write echo counts for '{site_name}' due to missing '{e}' in dmap data!")
        return

    scan = dmap_dict.get("scan", None)

    buf = echo_buffer[site_name]
    buf['total_echoes'] += num_echoes
    buf['ionospheric_echoes'] += num_ionosph_echoes
    buf['ground_scatter_echoes'] += num_grd_sctr_echoes
    buf['count'] += 1

    if scan == 1 and buf['count'] > 0:
        # Compute averages for the previous scan
        avg_total = int(buf['total_echoes'] / buf['count'])
        avg_iono = int(buf['ionospheric_echoes'] / buf['count'])
        avg_gs = int(buf['ground_scatter_echoes'] / buf['count'])

        echo_counts = EchoCounts(
            site_name=site_name,
            timestamp=dt.datetime.now(dt.timezone.utc),
            total_echoes=avg_total,
            ionospheric_echoes=avg_iono,
            ground_scatter_echoes=avg_gs
        )

        db.session.add(echo_counts)
        db.session.commit()
        logging.info(f"Stored averaged echo counts for {site_name}")

        # Reset buffer for the next scan
        echo_buffer[site_name] = {
            'total_echoes': 0,
            'ionospheric_echoes': 0,
            'ground_scatter_echoes': 0,
            'count': 0,
            'last_timestamp': None
        }

        return avg_total, avg_iono, avg_gs

    return None

def get_echo_counts(site_name: str, start_time, end_time) -> dict[str, list]:
    """
    Retrieve echo counts for a specific site within a time range,
    and return as a dictionary of lists (column-oriented), excluding id and site_name.
    """
    # Query the database
    query = EchoCounts.query.filter(
        EchoCounts.site_name == site_name,
        EchoCounts.timestamp >= start_time,
        EchoCounts.timestamp <= end_time
    ).order_by(EchoCounts.timestamp)

    # Convert to DataFrame
    data = [c.to_dict() for c in query.all()]
    if not data:
        return {}

    df = pd.DataFrame(data)
    # Drop 'id' and 'site_name' columns if they exist
    df = df.drop(columns=[col for col in ['id', 'site_name'] if col in df.columns])
    return df.to_dict(orient='list')

def get_num_echoes(dmap_dict: dict) -> tuple[int, int, int]:
    """
    Get number of echoes, number of ground scatter echoes,
    and number of ionospheric echoes in a dmap 

    :Args:
        dmap_dict (dict): The DMAP recieved from the socket
    
    :Returns:
        tuple[int, int, int]: A tuple containing:
            - num_echoes (int): Total number of echoes
            - num_ionosph_echoes (int): Number of ionospheric echoes
            - num_grd_sctr_echoes (int): Number of ground scatter echoes
    """
    # Total number of echoes is len(slist), which is number of velocity values in the dmap dict
    # Number of ground scatter echoes is the number of echoes where the ground scatter flag is 1
    # Number of ionospheric echoes is the number of echoes where the ground scatter flag is 0
    grd_sctr_flags = dmap_dict["gflg"].tolist()
    num_echoes = len(dmap_dict["gflg"].tolist())

    num_grd_sctr_echoes = grd_sctr_flags.count(1)
    num_ionosph_echoes = grd_sctr_flags.count(0)

    return num_echoes, num_ionosph_echoes, num_grd_sctr_echoes