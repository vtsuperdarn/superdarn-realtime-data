import io
import csv
import logging
import traceback
from dateutil.parser import parse
from flask import Blueprint, request, jsonify, make_response
from datetime import datetime, timedelta, timezone
from .data_processing.process_echoes import get_echo_counts

bp = Blueprint('main', __name__)

@bp.route('/echoes')
def echoes():
    site_name = request.args.get('site_name')
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    do_save_str = request.args.get('save')

    if not site_name:
        return jsonify({"message": "Missing required parameter: site_name"}), 400
    
    try:
        start_time = parse(start_str) if start_str else None
        end_time = parse(end_str) if end_str else None

        if start_time and end_time and start_time >= end_time:
            return jsonify({"message": "Invalid date range. Start time must be before end time."}), 400
    except ValueError:
        return jsonify({"message": "Invalid date format. Please use ISO format."}), 400

    if not end_time:
        end_time = datetime.now(timezone.utc)
    if not start_time:
        start_time = end_time - timedelta(hours=24)

    try:
        echo_counts = get_echo_counts(site_name, start_time, end_time)
    except Exception as e:
        logging.error(f"Error fetching echo counts for {site_name}:\n{traceback.format_exc()}")
        return jsonify({"message": "Error fetching echo counts.", "error": str(e)}), 500

    if not echo_counts:
        return jsonify({"message": "No echoes found for the specified date range."}), 404

    do_save = do_save_str.lower() == 'true' if do_save_str else False

    if do_save:
        echoes_csv = convert_echo_counts_to_csv(echo_counts)
        response = make_response(echoes_csv)

        # Set headers for CSV download
        response.headers["Content-Disposition"] = "attachment; filename=my_data.csv"
        response.headers["Content-Type"] = "text/csv"

        return response

    return echo_counts

def convert_echo_counts_to_csv(echo_counts):
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "total_echoes", "ionospheric_echoes", "ground_scatter_echoes"])

    # Get the columns as lists
    timestamps = echo_counts.get("timestamp", [])
    total_echoes = echo_counts.get("total_echoes", [])
    iono_echoes = echo_counts.get("ionospheric_echoes", [])
    ground_scatter = echo_counts.get("ground_scatter_echoes", [])

    # Write each row
    for row in zip(timestamps, total_echoes, iono_echoes, ground_scatter):
        writer.writerow(row)

    output.seek(0)
    return output.getvalue()