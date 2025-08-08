### SuperDARN Real-time Data Server

[Flask Socket IO](https://flask-socketio.readthedocs.io/en/latest/index.html) server providing access to realtime data from SuperDARN radars. Rather than connecting to radars directly from the front-end, this server aggregates data from multiple SuperDARN radars and sends them over a socket (Socket.IO protocol) in JSON format.

## Running the Server

### Initial setup

The main entry point is ``socket_server.py``. Radar IP addresses can be configured in ``radars.config.json``. See ``radars.config.json.example`` for an example. Canadian radars use a different socket protocol so they are defined differently. Define the address for the Canadian ZMQ socket server in the ``CANADA_ADDR`` environment variable.

### Setting up a Linux service

Currently, this server runs as a service ``rt-data-sockets`` on the ``superdarn`` machine. The config file can be found in ``/etc/systemd/system/rt-data-sockets.service``. It is defined as follows:
```conf
[Unit]
Description=Socket.IO Server for Real-time SuperDARN Data
After=network.target

[Service]
User=superdarn
WorkingDirectory=/var/www/html/superdarn-realtime-data
Environment="PATH=/var/www/html/superdarn-realtime-data/venv/bin"
Environment=PYTHONUNBUFFERED=1
ExecStart=/var/www/html/superdarn-realtime-data/.venv/bin/gunicorn -k eventlet -w 1 socket_server:app --bind 0.0.0.0:5003
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

``sudo systemctl enable rt-data-sockets`` will make the service run at startup. This only needs to be run once after you create the service.

### Starting/Stopping the Server
The following commands can be used to start/stop the server.
- **Start**: ``sudo systemctl start rt-data-sockets``
- **Stop**: ``sudo systemctl stop rt-data-sockets``
- **Retart**: ``sudo systemctl restart rt-data-sockets``

### Checking Server Status
To output the status of the server, run:<br>
``journalctl -u rt-data-sockets -f``
<br>or<br>
``journalctl -u rt-data-sockets --since="YYYY-MM-DD" > "service-output.txt"`` to send the output to a textfile starting from the date definedby ``--since="YYYY-MM-DD"``.

## File Structure

### run.py
- Main entry point
- Run in a shell to run in debug mode. Otherwise, start using the ``rt-data-sockets`` service

### ``app``
- ### socket_server.py
    - Handles starting the Flask Socket.IO server as well as starting the background tasks that listen to the radar sockets
- ### models.py
    - Where the database models are defined using Flask-SQLAlchemy's ORM
- ### routes.py
    - Where the Flask routes are defined
- ### utils.py
    - Helper functions
- ### extensions.py
    - Setup for Flask extensions
- ### ``radar_connections``
    - Functionality for connecting/disconnecting to SuperDARN radars
    - ### radar_client.py
        - Handles connecting/disconnecting to radar sockets and reading incoming packets
        - Currently, all radars other than the Canadian radars use the RadarClient for connections (standard socket protocol)
    - ### canada_connections.py
        - Handles connecting/disconnecting to Canadian radars which use ZMQ sockets
        - ZMQ is a different socket protocol which is why these radars have to be handled differently
- ### ``data_processing``
    - Files related to processing data received from the radars
    - ### process_dmap.py
        - Handles processing a DMAP packet as a JSON file
    - ### process_echoes.py
        - Handles extracting echoe from a DMAP packet
        - Storing echoes in SQL database
        - Averaging echoes over a scan

## Nginx Proxy Setup

An Nginx proxy is setup to hook up the vt.superdarn.org domain with this server. Configuration can be found in ``/etc/nginx/sites-available``. The server is defined as:
```nginx
server {
    listen 81;
    server_name vt.superdarn.org;

    location /socket.io/ {
        proxy_pass http://localhost:5003;
        proxy_http_version 1.1;
	    proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Proxy all other requests to Flask app
    location / {
        proxy_pass http://localhost:5003;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Handle OPTIONS preflight requests for CORS
        if ($request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
            add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization";
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
    }
}
```

Any connections to ``http://vt.superdarn.org:81/socket.io/`` are routed to ``http://localhost:5003`` where the Socket.IO server runs.
The '/' route is also proxied so any requests to regular Flask routes are also routed to ``http://localhost:5003``.

### Enabling the config

The config was enabled by adding a symlink to the ``sites-enabled`` folder which points to the config in ``sites-available``.

``sudo ln -s /etc/nginx/sites-available/superdarn-realtime-data /etc/nginx/sites-enabled/``

Next, restart nginx so that it runs the new server: ``sudo systemctl reload nginx``