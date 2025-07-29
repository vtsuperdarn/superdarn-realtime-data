# Handles processing echo count CSV files

import csv
import datetime as dt
import logging
import pandas as pd
import os

CSV_HEADERS = ['Timestamp', 'Beam_Number', 'Num_Echoes',
               'Num_Ionosph_Echoes', 'Num_Gnd_sctr_Echoes', 'Scan']

def get_echoes_csv(site_name: str):
    """Retrieves echoes CSV data for a given radar."""
    csv_dir = os.getenv('CSV_DIR')

    if not csv_dir:
        raise ValueError("CSV_DIR environment variable is not set.")
    
    subdir = dt.datetime.now().strftime("%Y-%m-%d")
    csv_path = os.path.join(csv_dir, subdir, f"{site_name}.csv")

    logging.debug(f"Looking for echoes CSV file: {csv_path}")

    if not os.path.exists(csv_path):
        logging.error(f"CSV file not found: {csv_path}")
        return None
    
    try:
        csv_file = pd.read_csv(csv_path)
        format_csv_timestamps(csv_file)
        logging.debug(f"Successfully read CSV file: {csv_path}")
    except Exception as e:
        logging.error(f"Error reading CSV file {csv_path}: {e}")
        return None

    try:
        return avg_echoes_over_scans(csv_file)
    except Exception as e:
        logging.error(f"Error averaging echoes in CSV for {site_name}: {e}")
        return None
    
def avg_echoes_over_scans(data):
    """Averages echoes over scans in the CSV data"""
    # Identify scan groups: increment group every time Scan == 1
    data['scan_group'] = (data['Scan'] == 1).cumsum()

    # Group by scan_group and aggregate
    grouped = data.groupby('scan_group').agg({
        'Timestamp': 'first',  # time at which scan started (Scan==1)
        'Num_Echoes': 'mean',
        'Num_Ionosph_Echoes': 'mean',
        'Num_Gnd_sctr_Echoes': 'mean'
    })

    return grouped.to_dict('list')

def format_csv_timestamps(csv_df: pd.DataFrame):
    csv_df['Timestamp'] = pd.to_datetime(csv_df['Timestamp'], format='%Y-%m-%d-%H:%M:%S.%f')
    csv_df['Timestamp'] = csv_df['Timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
    csv_df['Timestamp'] = csv_df['Timestamp'].str.slice(0, 23) + 'Z'  # Truncate to milliseconds and add 'Z'

def write_echoes_csv(dmap_dict: dict, site_name: str):
    """
    Write echoes data to a CSV file

    :Args:
        dmap_dict (dict): A DMAP dictionary containing radar data
    """
    now = dt.datetime.now()
    timestamp = now.strftime('%Y-%m-%d-%H:%M:%S.%f')

    output_dir = os.getenv('CSV_DIR')

    if not output_dir:
        raise ValueError("CSV_DIR environment variable is not set.")

    # Check if directory exists, create it if not
    subdir_name = now.strftime("%Y-%m-%d")
    subdir_path = os.path.join(output_dir, subdir_name)

    if not os.path.exists(subdir_path):
        logging.info(f"No directory exists for today ({subdir_name}), creating one...")
        os.mkdir(subdir_path)

    # Check if csv already exists, create it if not
    csv_path = os.path.join(subdir_path, site_name + ".csv")

    if not os.path.exists(csv_path):
        logging.info(f"No csv exists at '{csv_path}', creating one...")
        init_csv_file(csv_path)

    logging.info(f"Updating '{csv_path}' with latest data...")

    try:
        num_echoes, num_ionosph_echoes, num_grd_sctr_echoes = get_num_echoes(dmap_dict)
    except Exception as e:
        logging.error(f"Error getting echo counts for {site_name}: {e}")
        return

    with open(csv_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([timestamp, dmap_dict["bmnum"], num_echoes, num_ionosph_echoes, num_grd_sctr_echoes, dmap_dict["scan"]])

def init_csv_file(path: str):
    with open(path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADERS)


def get_num_echoes(dmap_dict: dict):
    """
    Get number of echoes, number of ground scatter echoes,
    and number of ionospheric echoes in a DMAP dictionary

    :Args:
        dmap_dict (dict): The DMAP dictionary containing radar data
    
    :Returns:
        tuple[int, int, int]: A tuple containing:
            - num_echoes (int): Total number of echoes
            - num_ionosph_echoes (int): Number of ionospheric echoes
            - num_grd_sctr_echoes (int): Number of ground scatter echoes
    """
    # Total number of echoes is len(slist), which is number of velocity values in the json packet
    # Number of ground scatter echoes is the number of echoes where the ground scatter flag is 1
    # Number of ionospheric echoes is the number of echoes where the ground scatter flag is 0
    grd_sctr_flags = dmap_dict["gflg"].tolist()
    num_echoes = len(grd_sctr_flags)

    num_grd_sctr_echoes = grd_sctr_flags.count(1)
    num_ionosph_echoes = grd_sctr_flags.count(0)

    return num_echoes, num_ionosph_echoes, num_grd_sctr_echoes