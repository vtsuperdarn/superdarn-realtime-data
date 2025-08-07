from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, timezone
from .data_processing.process_echoes import get_echo_counts

bp = Blueprint('main', __name__)

@bp.route('/echoes')
def echoes():
    site_name = request.args.get('site_name')

    if not site_name:
        return jsonify({"message": "Missing required parameter: site_name"}), 400
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=24)
    echo_counts = get_echo_counts(site_name, start_time, end_time)

    return echo_counts