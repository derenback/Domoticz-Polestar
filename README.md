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

## Polestar API access

The three credential fields are issued for Polestar Data Portal M2M/API access:

- **Account ID**: the Polestar API account or tenant identifier.
- **Client ID**: the OAuth 2.0 client identifier for the API application.
- **Client Secret**: the corresponding OAuth 2.0 client secret.

These values are not the Polestar app login or the vehicle VIN. Sign in to the
[Polestar Data Portal](https://data-portal.polestar.com/se/auth) to obtain or
manage the API account details. If API access is not enabled for your account,
request it through the Polestar API onboarding or support contact associated
with your account. The API endpoint used by this plugin is the EU North 1 M2M
endpoint.

No numeric request quota is documented in the API material used by this plugin.
The exact limit may depend on the API account or application, so check the
terms or onboarding information supplied with your credentials. Each poll uses
one vehicle-list request plus six telemetry requests per vehicle, in addition
to token authentication. Keep the default five-minute interval unless your
account explicitly permits more frequent polling; increase the interval if
the API returns HTTP 429 (Too Many Requests).
