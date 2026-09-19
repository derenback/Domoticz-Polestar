# Domoticz Polestar plugin

Reads Polestar Data Portal telemetry and creates Domoticz devices for:

- Battery charge percentage
- Charger connection status
- Central lock status
- Estimated driving range
- Charging status
- Odometer
- Vehicle location
- Service warning
- Availability status

## Installation

Clone the repository into the Domoticz plugins directory:

```sh
cd /opt/domoticz/config/plugins
git clone https://github.com/derenback/Domoticz-Polestar.git Polestar
```

Restart Domoticz, then add **Polestar** under **Setup -> Hardware**. Enter the
Polestar Data Portal `Account ID`, `Client ID`, and `Client Secret` as the
plugin settings. The optional `Vehicle ID` can restrict the plugin to one VIN;
leave it blank to monitor all vehicles.

The plugin polls every five minutes by default. The minimum polling interval is
60 seconds. Credentials are stored in Domoticz hardware settings, so protect
access to the Domoticz database and web interface.