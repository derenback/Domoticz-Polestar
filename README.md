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
- Telemetry availability status
- Engine hours to service
- Days to service
- Distance to service
- Average speed
- Automatic average speed
- Average energy consumption

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

The plugin polls every five minutes by default. The technical minimum polling
interval is 60 seconds. The default interval is within the daily API quota for
one vehicle; increase it for multiple vehicles.
Credentials are stored in Domoticz hardware settings, so protect access to the
Domoticz database and web interface.

## Polestar API access

The three credential fields are issued for Polestar Data Portal M2M/API access:

- **Account ID**: the Polestar API account or tenant identifier.
- **Client ID**: the OAuth 2.0 client identifier for the API application.
- **Client Secret**: the corresponding OAuth 2.0 client secret.

These values are not the Polestar app login or the vehicle VIN. Sign in to the
[Polestar Data Portal](https://data-portal.polestar.com/) to obtain or
manage the API account details. If API access is not enabled for your account,
request it through the Polestar API onboarding or support contact associated
with your account. The API endpoint used by this plugin is the EU North 1 M2M
endpoint.

Polestar limits the API to **10,000 requests per day** and **100 requests per
minute**. For one vehicle, each plugin poll currently uses:

- OAuth token request when the cached token expires
- 1 vehicle-list request
- 6 telemetry requests: availability, battery, location, health, odometer,
  and exterior

That is 7 requests per poll for one vehicle, plus an occasional OAuth token
request when the cached token expires. At the default five-minute interval,
this is approximately 2,016 requests per day, plus token renewals, well below
the daily limit and the per-minute limit. The 60-second technical minimum would
use up to 10,080 requests per day before token renewals, so a practical
recommended minimum is 2 minutes for one vehicle. Each additional vehicle adds
6 telemetry requests per poll; increase the interval further for multiple
vehicles, and increase it if the API returns HTTP 429 (Too Many Requests).
