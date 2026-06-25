# Domoticz TP-Link Router Plugin

Domoticz plugin for monitoring and controlling TP-Link routers supported by the `tplinkrouterc6u` Python library.

## Features

- Control WiFi 2.4 GHz
- Control WiFi 5 GHz
- Control Guest WiFi 2.4 GHz
- Control Guest WiFi 5 GHz
- Internet status
- Total connected clients
- WiFi clients
- Wired clients
- Guest clients
- Background command queue for faster Domoticz UI response
- Automatic polling to keep Domoticz synchronized with the real router state
- Isolated Python virtual environment installation

## Tested devices

- TP-Link Archer AX20 v1

## Compatibility

This plugin may work with other TP-Link routers supported by the `tplinkrouterc6u` library, but compatibility is not guaranteed.

Community testing is welcome.

## Installation

Clone this repository and run the installer:

```bash
cd /home/pi/domoticz/plugins
git clone https://github.com/blooesky/Domoticz-TPLinkRouter.git TPLinkRouter
cd TPLinkRouter
chmod +x install.sh
./install.sh
```

If Domoticz is installed somewhere else:

```bash
DOMOTICZ_DIR=/opt/domoticz ./install.sh
```

The installer will:

- copy the plugin to `/home/pi/domoticz/plugins/TPLinkRouter`
- create an isolated Python virtual environment in `/home/pi/domoticz/plugins/TPLinkRouter/venv`
- install Python dependencies only inside that virtual environment
- verify required imports
- check plugin syntax
- restart Domoticz if possible

## Configuration

After installation:

1. Open Domoticz.
2. Go to **Setup -> Hardware**.
3. Add new hardware.
4. Select **TP-Link Router**.

Recommended settings:

- Router IP / Host: `192.168.0.1`
- Username: `admin`
- Password: your local router admin password
- Poll interval: `180`
- Scheme: `HTTPS`
- Verify SSL: `False`

## Devices created

The plugin creates the following Domoticz devices:

- WiFi 2.4G
- WiFi 5G
- Guest WiFi 2.4G
- Guest WiFi 5G
- Internet
- Connected Clients
- WiFi Clients
- Wired Clients
- Guest Clients

## Notes

- Use the router local admin password, not a TP-Link cloud account password.
- Keep SSL verification disabled if your router uses a weak or self-signed HTTPS certificate.
- Avoid very short polling intervals. `180` seconds is recommended.
- TP-Link web sessions can be sensitive to multiple simultaneous logins.
- Dependencies are isolated in the plugin `venv/` directory.

## Troubleshooting

### Plugin does not appear in Domoticz

Check that the plugin is installed here:

```bash
/home/pi/domoticz/plugins/TPLinkRouter/plugin.py
```

Then restart Domoticz:

```bash
sudo systemctl restart domoticz
```

### Python dependency errors

Run:

```bash
cd /home/pi/domoticz/plugins/TPLinkRouter
venv/bin/python -m pip install -r requirements.txt
```

### Login failed

Check:

- router IP address
- username
- local router admin password
- whether another active router web session is blocking login

## Credits

This plugin uses the `tplinkrouterc6u` Python library.
