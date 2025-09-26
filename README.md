### SuperDARN Real-time Data Server

[Flask Socket IO](https://flask-socketio.readthedocs.io/en/latest/index.html) server providing access to realtime data from SuperDARN radars. Rather than connecting to radars directly from the front-end, this server aggregates data from multiple SuperDARN radars and sends them over a socket (Socket.IO protocol) in JSON format.

## Running the Server

### Starting/Stopping the Server
The following commands can be used to start/stop the server.
- **Start**: ``sudo systemctl start rt-data-sockets``
- **Stop**: ``sudo systemctl stop rt-data-sockets``
- **Retart**: ``sudo systemctl restart rt-data-sockets``

### Output Server Status to Terminal
To view a life feed of the server output in the terminal, run:<br>
``journalctl -u rt-data-sockets -f``

### Accessing Logs
You can also output logs for a particular time range using the `--since="YYYY-MM-DD"` flag and, optionally, the `--until="YYYY-MM-DD"` flag. If `--until` is not specified, it will collect logs starting from `--since`.

Ex:
``journalctl -u rt-data-sockets --since="YYYY-MM-DD" > "service-output.txt"``

## Adding New Radars

The server expects each radar to send a binary stream of the DMAP file over TCP. Define the radar IP addresses in a file called ``radars.config.json``. An example file ``radars.config.json.example`` is provided as an example.

#### Example Entry
    "kod" : {
        "host": "<host-ip>",
        "port": 9999
    }

### SuperDARN Canada Radars
The Canadian radars use a library called "[ZeroMQ](https://zeromq.org/socket-api/)" (ZMQ). ZMQ is a high-level messaging library that sits on top of regular sockets.

All Canadian radars send data from the ZMQ socket server which is defined in the ``CANADA_ADDR`` environment variable (see `.env.example` for an example). The ZMQ connections are handled in ``app/radar_connections/canada_zmq_connections.py``.

### Updating the Front-end (Important)

There is also a config file on the front-end that needs to be updated when a new radar is added. Steps for updating this config file is provided on the [front-end README](https://github.com/vtsuperdarn/vt-superdarn-flask/tree/main/app/static/js/real-time-plots).

## Environment Variables

There should be a ``.env`` file in this directory that defines the environment variables. See ``.env.example`` for an example.

## How Echo Counts are Stored

The echo counts are stored in a SQLite database (`app/database.sqlite`) and are only kept for a particular time range defined by the `MAX_DAYS_STORE_ECHOES` environment variable.

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
    - ### canada_zmq_connections.py
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

## Server Setup

The following sections explain how to setup the server to run as a service. An Nginx proxy also has to be set up as well which is explained in this section.

### Service Setup

The server runs as a service called ``rt-data-sockets``. The config file can be found in ``/etc/systemd/system/rt-data-sockets.service``. It is defined as follows:
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

After initially creating the service, run the following commands: 
1. ``sudo systemctl daemon-reload`` - Reloads files so that the new service is recognized
2. ``sudo systemctl enable rt-data-sockets`` - Makes `rt-data-sockets` run at startup
3. ``sudo systemctl start rt-data-sockets.service`` - Starts the service

### Nginx Proxy Setup

Nginx is an intermediary server that lets you reroute requests to different servers based on a URL path. This is needed so that the server can be accessed at the domain ``vt.superdarn.org``. In this case, the real-time Flask server runs at ``http://localhost:5003``. The proxy server reroutes requests from ``vt.superdarn.org`` to ``http://localhost:5003``. There is also some additional setup for ``Socket.IO`` to ensure that the socket connections are handled properly ([more info here](https://socket.io/docs/v3/reverse-proxy/#nginx)). This also provides an extra layer of security, as the IP addresses of the backend servers are hidden from clients.

The configuration is defined in ``/etc/nginx/sites-available``. The server is defined as:
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

### Enabling the Config (first-time setup)

*These steps only need to be completed when setting up the server for the first time.*

1. Enable the config by adding a symlink to the ``sites-enabled`` folder which points to the config in ``sites-available``.

``sudo ln -s /etc/nginx/sites-available/superdarn-realtime-data /etc/nginx/sites-enabled/``

2. Restart nginx so that it runs the new server: ``sudo systemctl reload nginx``