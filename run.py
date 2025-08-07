"""Main entry point for the SuperDARN Realtime Data application."""
import logging
from app import create_app

app, socketio = create_app()

if __name__ == '__main__':
    logging.info("Starting dev server...")
    socketio.run(app, host='0.0.0.0', port=5003, debug=True)