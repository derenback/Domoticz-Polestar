#!/usr/bin/env python3
"""Domoticz plugin for Polestar Data Portal telemetry."""

"""
<plugin key="POLESTAR" name="Polestar" version="0.1.0" author="Derenback">
    <description>
        <h2>Polestar Data Portal</h2>
        <p>Shows battery, charging, vehicle status, location, and service information.</p>
    </description>
    <params>
        <param field="Mode1" label="Account ID" width="300px" required="true" default="" />
        <param field="Mode2" label="Client ID" width="300px" required="true" default="" />
        <param field="Mode3" label="Client Secret" width="300px" required="true" default="" />
        <param field="Mode4" label="Reading interval (seconds)" width="75px" required="true" default="300" />
        <param field="Mode5" label="Vehicle ID (optional)" width="300px" default="" />
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="On" value="Debug" />
                <option label="Off" value="Off" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

import base64
import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

import Domoticz


DEFAULT_BASE_URL = "https://pc-api.polestar.com/eu-north-1/data-portal/m2m/"
DEFAULT_TOKEN_URL = DEFAULT_BASE_URL + "token"
REQUEST_TIMEOUT_SECONDS = 30
HEARTBEAT_SECONDS = 10

UNIT_BATTERY = 1
UNIT_CHARGER = 2
UNIT_LOCK = 3
UNIT_RANGE = 4
UNIT_CHARGING = 5
UNIT_ODOMETER = 6
UNIT_LOCATION = 7
UNIT_SERVICE = 8
UNIT_AVAILABILITY = 9
UNITS_PER_VEHICLE = 9


def _request_json(request: Request) -> Any:
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError("HTTP %s: %s" % (error.code, details[:200])) from error
    except URLError as error:
        raise RuntimeError("request failed: %s" % error.reason) from error
    except json.JSONDecodeError as error:
        raise RuntimeError("response was not JSON") from error


def _get_access_token(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode((client_id + ":" + client_secret).encode()).decode()
    request = Request(
        DEFAULT_TOKEN_URL,
        data=urlencode({"grant_type": "client_credentials"}).encode(),
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": "Basic " + credentials,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    response = _request_json(request)
    if not isinstance(response, dict):
        raise RuntimeError("token response was not an object")
    token = response.get("access_token") or response.get("accessToken")
    if not token:
        raise RuntimeError("token response did not contain an access token")
    return str(token)


def _fetch(token: str, account_id: str, path: str) -> Any:
    request = Request(
        urljoin(DEFAULT_BASE_URL, path.lstrip("/")),
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer " + token,
            "x-client-id": account_id,
            "X-Account-Id": account_id,
        },
    )
    return _request_json(request)


def _telemetry_value(telemetry: Any, field: str, default: Any = None) -> Any:
    if not isinstance(telemetry, dict):
        return default
    data = telemetry.get("data")
    if not isinstance(data, dict):
        return default
    return data.get(field, default)


def _status_label(value: Any) -> str:
    text = str(value or "Unknown")
    for prefix in (
        "AVAILABILITY_STATUS_",
        "CHARGER_CONNECTION_STATUS_",
        "CHARGING_STATUS_V2_",
        "CHARGING_STATUS_",
        "SERVICE_WARNING_",
        "LOCK_STATUS_",
    ):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.replace("_", " ").title()


def _unit_for_vehicle(index: int, offset: int) -> int:
    return (index * UNITS_PER_VEHICLE) + offset


class BasePlugin:
    def __init__(self) -> None:
        self.account_id = ""
        self.client_id = ""
        self.client_secret = ""
        self.vehicle_id = ""
        self.interval = 300
        self.heartbeat_count = 0
        self.debug = False

    def onStart(self) -> None:
        self.account_id = Parameters["Mode1"].strip()
        self.client_id = Parameters["Mode2"].strip()
        self.client_secret = Parameters["Mode3"].strip()
        self.vehicle_id = Parameters["Mode5"].strip()
        self.debug = Parameters["Mode6"] == "Debug"
        try:
            self.interval = max(60, int(Parameters["Mode4"]))
        except (KeyError, ValueError):
            self.interval = 300

        Domoticz.Log("POLESTAR: plugin started")
        Domoticz.Heartbeat(HEARTBEAT_SECONDS)
        self.heartbeat_count = 0

    def onStop(self) -> None:
        Domoticz.Log("POLESTAR: plugin stopped")

    def onHeartbeat(self) -> None:
        if self.heartbeat_count > 0:
            self.heartbeat_count -= HEARTBEAT_SECONDS
            return
        self.heartbeat_count = self.interval
        try:
            self._poll()
        except Exception as error:
            Domoticz.Log("POLESTAR: %s" % error)

    def _poll(self) -> None:
        if not self.account_id or not self.client_id or not self.client_secret:
            raise RuntimeError("Account ID, Client ID, and Client Secret are required")

        token = _get_access_token(self.client_id, self.client_secret)
        response = _fetch(token, self.account_id, "/v1/vehicles")
        vehicle_ids = response.get("data", []) if isinstance(response, dict) else []
        vehicle_ids = [str(value) for value in vehicle_ids if value]
        if self.vehicle_id:
            vehicle_ids = [value for value in vehicle_ids if value == self.vehicle_id]
        vehicle_ids.sort()

        for index, vehicle_id in enumerate(vehicle_ids):
            telemetry = {
                endpoint: _fetch(
                    token,
                    self.account_id,
                    "/v1/vehicles/%s/telemetry/%s" % (vehicle_id, endpoint),
                )
                for endpoint in (
                    "availability",
                    "battery",
                    "location",
                    "health",
                    "odometer",
                    "exterior",
                )
            }
            self._ensure_devices(index)
            self._update_vehicle(index, telemetry)

        if self.debug:
            Domoticz.Log("POLESTAR: updated %d vehicle(s)" % len(vehicle_ids))

    def _ensure_devices(self, index: int) -> None:
        definitions = (
            (UNIT_BATTERY, "Battery", 243, 6),
            (UNIT_CHARGER, "Charger", 243, 19),
            (UNIT_LOCK, "Lock", 244, 73),
            (UNIT_RANGE, "Range", 243, 31),
            (UNIT_CHARGING, "Charging", 243, 19),
            (UNIT_ODOMETER, "Odometer", 243, 31),
            (UNIT_LOCATION, "Location", 243, 19),
            (UNIT_SERVICE, "Service", 243, 19),
            (UNIT_AVAILABILITY, "Telemetry", 243, 19),
        )
        for offset, device_name, device_type, subtype in definitions:
            unit = _unit_for_vehicle(index, offset)
            if unit not in Devices:
                if device_name in ("Range", "Odometer"):
                    Domoticz.Device(
                        Name=device_name,
                        Unit=unit,
                        Type=device_type,
                        Subtype=subtype,
                        Options={"Custom": "1;km"},
                        Used=1,
                    ).Create()
                else:
                    Domoticz.Device(
                        Name=device_name,
                        Unit=unit,
                        Type=device_type,
                        Subtype=subtype,
                        Used=1,
                    ).Create()

    def _update_vehicle(self, index: int, telemetry: Dict[str, Any]) -> None:
        battery = telemetry.get("battery")
        location = telemetry.get("location")
        health = telemetry.get("health")
        odometer = telemetry.get("odometer")
        availability = telemetry.get("availability")
        exterior = telemetry.get("exterior")
        battery_level = _telemetry_value(battery, "batteryChargeLevelPercentage")
        charger = _status_label(_telemetry_value(battery, "chargerConnectionStatus"))
        lock = _status_label(_telemetry_value(exterior, "centralLock"))
        charging = _status_label(_telemetry_value(battery, "chargingStatusV2"))
        range_km = _telemetry_value(battery, "estimatedDistanceToEmptyKm")
        odometer_meters = _telemetry_value(odometer, "odometerMeters")
        coordinate = _telemetry_value(location, "coordinate")
        service = _status_label(_telemetry_value(health, "serviceWarning"))
        availability_status = _status_label(
            _telemetry_value(availability, "availabilityStatus")
        )
        location_value = "Unknown"
        if isinstance(coordinate, dict):
            latitude = coordinate.get("latitude")
            longitude = coordinate.get("longitude")
            if latitude is not None and longitude is not None:
                location_value = "%.5f, %.5f" % (float(latitude), float(longitude))
        odometer_value = "Unknown"
        if odometer_meters is not None:
            odometer_value = "%.1f" % (float(odometer_meters) / 1000)
        units = (
            (_unit_for_vehicle(index, UNIT_BATTERY), battery_level, str(battery_level or "0")),
            (_unit_for_vehicle(index, UNIT_CHARGER), charger, charger),
            (_unit_for_vehicle(index, UNIT_RANGE), range_km, str(range_km)),
            (_unit_for_vehicle(index, UNIT_CHARGING), charging, charging),
            (_unit_for_vehicle(index, UNIT_ODOMETER), odometer_meters, odometer_value),
            (_unit_for_vehicle(index, UNIT_LOCATION), location_value, location_value),
            (_unit_for_vehicle(index, UNIT_SERVICE), service, service),
            (_unit_for_vehicle(index, UNIT_AVAILABILITY), availability_status, availability_status),
        )
        for unit, value, display_value in units:
            if unit in Devices and value is not None:
                Devices[unit].Update(nValue=1, sValue=display_value)
        lock_unit = _unit_for_vehicle(index, UNIT_LOCK)
        if lock_unit in Devices and lock != "Unknown":
            Devices[lock_unit].Update(
                nValue=1 if lock == "Locked" else 0,
                sValue="On" if lock == "Locked" else "Off",
            )


_plugin = BasePlugin()


def onStart() -> None:
    _plugin.onStart()


def onStop() -> None:
    _plugin.onStop()


def onHeartbeat() -> None:
    _plugin.onHeartbeat()