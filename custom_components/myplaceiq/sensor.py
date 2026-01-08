import json
import logging
import time  # Added import
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

logger = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up MyPlaceIQ sensor entities from a config entry."""
    logger.debug("Setting up sensor entities for MyPlaceIQ")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    data = coordinator.data

    if not isinstance(data, dict) or not data or "body" not in data:
        logger.error("Invalid or missing coordinator data: %s", data)
        return

    try:
        body = json.loads(data["body"])
    except (json.JSONDecodeError, TypeError) as err:
        logger.error("Failed to parse coordinator data body: %s", err)
        return

    aircons = body.get("aircons", {})
    zones = body.get("zones", {})

    entities = []

    # AC System Sensors (Mode and State)
    for aircon_id, aircon_data in aircons.items():
        entities.extend([
            MyPlaceIQAirconSensor(
                coordinator,
                config_entry,
                aircon_id,
                aircon_data
            ),
            MyPlaceIQAirconStateSensor(
                coordinator,
                config_entry,
                aircon_id,
                aircon_data
            )
        ])

    # Zone Sensors (Temperature and State)
    for aircon_id, aircon_data in aircons.items():
        for zone_id in aircon_data.get("zoneOrder", []):
            zone_data = zones.get(zone_id)
            if zone_data and zone_data.get("isVisible", False):
                entities.extend([
                    MyPlaceIQZoneSensor(
                        coordinator,
                        config_entry,
                        zone_id,
                        zone_data,
                        aircon_id
                    ),
                    MyPlaceIQZoneStateSensor(
                        coordinator,
                        config_entry,
                        zone_id,
                        zone_data,
                        aircon_id
                    )
                ])

    if entities:
        async_add_entities(entities)
        logger.debug("Added %d sensor entities", len(entities))
    else:
        logger.warning("No sensor entities created; check data structure")

class MyPlaceIQAirconSensor(CoordinatorEntity, SensorEntity):
    # pylint: disable=too-many-instance-attributes
    """Sensor for MyPlaceIQ AC system mode."""

    def __init__(self, coordinator, config_entry, aircon_id, aircon_data):
        super().__init__(coordinator)
        self._aircon_id = aircon_id
        self._config_entry = config_entry
        self._name = aircon_data.get("name", "Aircon")
        self._attr_unique_id = f"{config_entry.entry_id}_aircon_{aircon_id}_mode"
        self._attr_name = f"{self._name}_mode".replace(" ", "_").lower()
        self._attr_icon = "mdi:air-conditioner"
        self._attr_device_class = None
        self._attr_state_class = None
        self._last_known_is_on = None

    @property
    def state(self):
        """Return the state of the AC (mode or off)."""
        data = self.coordinator.data
        if not isinstance(data, dict) or not data or "body" not in data:
            logger.debug("No valid coordinator data for aircon %s", self._attr_unique_id)
            return None
        try:
            body = json.loads(data["body"])
            aircon = body.get("aircons", {}).get(self._aircon_id, {})
            is_on = aircon.get("isOn",
                self._last_known_is_on if self._last_known_is_on is not None else False)
            if is_on:
                self._last_known_is_on = is_on
            state = aircon.get("mode", "unknown") if is_on else "off"
            logger.debug("Aircon %s mode state updated at %s: %s (isOn=%s, mode=%s)",
                         self._attr_unique_id, time.strftime("%H:%M:%S"), state, is_on,
                         aircon.get("mode", "missing"))
            return state
        except (json.JSONDecodeError, TypeError) as err:
            logger.error("Failed to parse coordinator data for aircon %s: %s",
                self._attr_unique_id, err)
            return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes for the AC."""
        data = self.coordinator.data
        if not isinstance(data, dict) or not data or "body" not in data:
            logger.debug("No valid coordinator data for aircon attributes %s", self._attr_unique_id)
            return {}
        try:
            body = json.loads(data["body"])
            aircon = body.get("aircons", {}).get(self._aircon_id, {})
            attributes = {
                "is_on": aircon.get("isOn",
                    self._last_known_is_on if self._last_known_is_on is not None else False),
                "actual_temperature": aircon.get("actualTemperature"),
                "target_temperature_heat": aircon.get("targetTemperatureHeat"),
                "target_temperature_cool": aircon.get("targetTemperatureCool"),
                "fan_speed_heat": aircon.get("fanSpeedHeat"),
                "allowed_modes": aircon.get("allowedModes", []),
                "aircon_state": aircon.get("airconState")
            }
            logger.debug("Aircon %s attributes updated at %s: %s",
                         self._attr_unique_id, time.strftime("%H:%M:%S"), attributes)
            return attributes
        except (json.JSONDecodeError, TypeError) as err:
            logger.error("Failed to parse coordinator data for aircon attributes %s: %s",
                self._attr_unique_id, err)
            return {}

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._config_entry.entry_id}_aircon_{self._aircon_id}")},
            "name": f"Aircon {self._name}",
            "manufacturer": "MyPlaceIQ",
            "model": "Aircon",
        }

class MyPlaceIQAirconStateSensor(CoordinatorEntity, SensorEntity):
    # pylint: disable=too-many-instance-attributes
    """Sensor for MyPlaceIQ AC system on/off state."""

    def __init__(self, coordinator, config_entry, aircon_id, aircon_data):
        super().__init__(coordinator)
        self._aircon_id = aircon_id
        self._config_entry = config_entry
        self._name = aircon_data.get("name", "Aircon")
        self._attr_unique_id = f"{config_entry.entry_id}_aircon_{aircon_id}_state"
        self._attr_name = f"{self._name}_state".replace(" ", "_").lower()
        self._attr_icon = "mdi:power"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._last_known_is_on = None

    @property
    def state(self):
        """Return the on/off state of the AC."""
        data = self.coordinator.data
        if not isinstance(data, dict) or not data or "body" not in data:
            logger.debug("No valid coordinator data for aircon state %s", self._attr_unique_id)
            return None
        try:
            body = json.loads(data["body"])
            aircon = body.get("aircons", {}).get(self._aircon_id, {})
            is_on = aircon.get("isOn",
                self._last_known_is_on if self._last_known_is_on is not None else False)
            if is_on:
                self._last_known_is_on = is_on
            state = "on" if is_on else "off"
            logger.debug("Aircon %s state updated at %s: %s (isOn=%s)",
                         self._attr_unique_id, time.strftime("%H:%M:%S"), state, is_on)
            return state
        except (json.JSONDecodeError, TypeError) as err:
            logger.error("Failed to parse coordinator data for aircon state %s: %s",
                self._attr_unique_id, err)
            return None

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._config_entry.entry_id}_aircon_{self._aircon_id}")},
            "name": f"Aircon {self._name}",
            "manufacturer": "MyPlaceIQ",
            "model": "Aircon",
        }

class MyPlaceIQZoneSensor(CoordinatorEntity, SensorEntity):
    # pylint: disable=too-many-instance-attributes
    """Sensor for MyPlaceIQ zone temperature."""

    def __init__(self, coordinator, config_entry, zone_id, zone_data, aircon_id):
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-positional-arguments
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._aircon_id = aircon_id
        self._config_entry = config_entry
        self._name = zone_data.get("name", "Zone")
        self._attr_unique_id = f"{config_entry.entry_id}_zone_{zone_id}_temperature"
        self._attr_name = f"{self._name}_temperature".replace(" ", "_").lower()
        self._attr_icon = "mdi:thermostat"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def state(self):
        """Return the current temperature of the zone."""
        data = self.coordinator.data
        if not isinstance(data, dict) or not data or "body" not in data:
            logger.debug("No valid coordinator data for zone temperature %s", self._attr_unique_id)
            return None
        try:
            body = json.loads(data["body"])
            zone = body.get("zones", {}).get(self._zone_id, {})
            state = zone.get("temperatureSensorValue")
            logger.debug("Zone %s temperature state updated at %s: %s",
                         self._attr_unique_id, time.strftime("%H:%M:%S"), state)
            return state
        except (json.JSONDecodeError, TypeError) as err:
            logger.error("Failed to parse coordinator data for zone temperature %s: %s",
                self._attr_unique_id, err)
            return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes for the zone."""
        data = self.coordinator.data
        if not isinstance(data, dict) or not data or "body" not in data:
            logger.debug("No valid coordinator data for zone attributes %s", self._attr_unique_id)
            return {}
        try:
            body = json.loads(data["body"])
            zone = body.get("zones", {}).get(self._zone_id, {})
            attributes = {
                "is_on": zone.get("isOn", False),
                "aircon_mode": zone.get("airconMode"),
                "target_temperature_heat": zone.get("targetTemperatureHeat"),
                "target_temperature_cool": zone.get("targetTemperatureCool"),
                "zone_type": zone.get("zoneType"),
                "is_clickable": zone.get("isClickable")
                "isPriorityZoneActive": zone.get("isPriorityZoneActive")
                "isPriorityZone": zone.get("isPriorityZone")
                "airconMode": zone.get("airconMode")
                "targetPercentCool": zone.get("targetPercentCool")
                "targetPercentHeat": zone.get("targetPercentHeat")
                "actualPercent": zone.get("actualPercent")
            }
            logger.debug("Zone %s attributes updated at %s: %s",
                         self._attr_unique_id, time.strftime("%H:%M:%S"), attributes)
            return attributes
        except (json.JSONDecodeError, TypeError) as err:
            logger.error("Failed to parse coordinator data for zone attributes %s: %s",
                self._attr_unique_id, err)
            return {}

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._config_entry.entry_id}_zone_{self._zone_id}")},
            "name": f"Zone {self._name}",
            "manufacturer": "MyPlaceIQ",
            "model": "Zone",
            "via_device": (DOMAIN, f"{self._config_entry.entry_id}_aircon_{self._aircon_id}")
        }

class MyPlaceIQZoneStateSensor(CoordinatorEntity, SensorEntity):
    # pylint: disable=too-many-instance-attributes
    """Sensor for MyPlaceIQ zone on/off state."""

    def __init__(self, coordinator, config_entry, zone_id, zone_data, aircon_id):
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-positional-arguments
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._aircon_id = aircon_id
        self._config_entry = config_entry
        self._name = zone_data.get("name", "Zone")
        self._attr_unique_id = f"{config_entry.entry_id}_zone_{zone_id}_state"
        self._attr_name = f"{self._name}_state".replace(" ", "_").lower()
        self._attr_icon = "mdi:toggle-switch"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self):
        """Return the on/off state of the zone."""
        data = self.coordinator.data
        if not isinstance(data, dict) or not data or "body" not in data:
            logger.debug("No valid coordinator data for zone state %s", self._attr_unique_id)
            return None
        try:
            body = json.loads(data["body"])
            zone = body.get("zones", {}).get(self._zone_id, {})
            state = "on" if zone.get("isOn", False) else "off"
            logger.debug("Zone %s state updated at %s: %s (isOn=%s)",
                         self._attr_unique_id, time.strftime("%H:%M:%S"),
                            state, zone.get("isOn", "missing"))
            return state
        except (json.JSONDecodeError, TypeError) as err:
            logger.error("Failed to parse coordinator data for zone state %s: %s",
                self._attr_unique_id, err)
            return None

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._config_entry.entry_id}_zone_{self._zone_id}")},
            "name": f"Zone {self._name}",
            "manufacturer": "MyPlaceIQ",
            "model": "Zone",
            "via_device": (DOMAIN, f"{self._config_entry.entry_id}_aircon_{self._aircon_id}")
        }
