import eventlet
eventlet.monkey_patch()  # Patch standard library to use eventlet (for SocketIO)

from dotenv import load_dotenv
load_dotenv()

import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from .extensions import db 
from .socket_server import start_socketio_listeners
from .utils import schedule_echo_deletion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_app():
    """Create and configure the Flask application. Returns the Flask application instance and SocketIO instance"""
    app = Flask(__name__)

    CORS(app, origins=[
        "http://localhost:5002",
        "http://127.0.0.1:5002",
        "http://localhost",
        "http://127.0.0.1",
        "vt.superdarn.org",
        "vt.superdarn.org:5002",
        "vt.superdarn.org:5003"
    ])

    # Configure Flask
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret')

    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database.sqlite')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable tracking modifications for performance

    db.init_app(app)
    
    with app.app_context(): 
        db.create_all()
        
    schedule_echo_deletion(app)

    # Configure SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    start_socketio_listeners(socketio, app)

    from . import routes
    app.register_blueprint(routes.bp)

    return app, socketio