import logging
import traceback
from dateutil.parser import parse
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, timezone
from .data_processing.process_echoes import get_echo_counts

bp = Blueprint('main', __name__)

@bp.route('/echoes')
def echoes():
    site_name = request.args.get('site_name')
    start_str = request.args.get('start')
    end_str = request.args.get('end')

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

    return echo_counts