"""Sensor platform for MyUsage integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyUsageCoordinator

UNIT_GAL = "gal"


def _parse_posted(posted: str):
    """Parse posted date string (MM/DD/YYYY HH:MM AM/PM) to UTC datetime."""
    if not posted:
        return None
    try:
        return datetime.strptime(posted, "%m/%d/%Y %I:%M %p").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(posted.split(" ")[0], "%m/%d/%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


@dataclass(frozen=True, kw_only=True)
class MyUsageSensorDescription(SensorEntityDescription):
    value_fn: callable = None
    attr_fn:  callable = None


SENSORS: tuple[MyUsageSensorDescription, ...] = (
    MyUsageSensorDescription(
        key="electric_kwh",
        name="Electric",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:lightning-bolt",
        value_fn=lambda d: d["electric"]["last_kwh"],
        attr_fn=lambda d: {
            "posted":   d["electric"]["posted"],
            "from":     d["electric"]["from"],
            "to":       d["electric"]["to"],
            "type":     d["electric"]["type"],
            "reading":  d["electric"]["reading"],
            "meter":    d["meters"]["electric"],
        },
    ),
    MyUsageSensorDescription(
        key="electric_kw",
        name="Electric Peak Demand",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        icon="mdi:flash",
        value_fn=lambda d: d["electric"]["last_kw"],
        attr_fn=None,
    ),
    MyUsageSensorDescription(
        key="water_gal",
        name="Water",
        native_unit_of_measurement=UNIT_GAL,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water",
        value_fn=lambda d: d["water"]["last_gal"],
        attr_fn=lambda d: {
            "posted":  d["water"]["posted"],
            "type":    d["water"]["type"],
            "reading": d["water"]["reading"],
            "meter":   d["meters"]["water"],
        },
    ),
    MyUsageSensorDescription(
        key="reclaimed_gal",
        name="Reclaimed Water",
        native_unit_of_measurement=UNIT_GAL,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:recycle",
        value_fn=lambda d: d["reclaimed"]["last_gal"],
        attr_fn=lambda d: {
            "posted":  d["reclaimed"]["posted"],
            "type":    d["reclaimed"]["type"],
            "reading": d["reclaimed"]["reading"],
            "meter":   d["meters"]["reclaimed"],
        },
    ),
    MyUsageSensorDescription(
        key="electric_last_posted",
        name="Electric Last Posted",
        icon="mdi:clock-outline",
        value_fn=lambda d: d["electric"]["posted"],
        attr_fn=None,
    ),
    MyUsageSensorDescription(
        key="water_last_posted",
        name="Water Last Posted",
        icon="mdi:clock-outline",
        value_fn=lambda d: d["water"]["posted"],
        attr_fn=None,
    ),
    MyUsageSensorDescription(
        key="reclaimed_last_posted",
        name="Reclaimed Water Last Posted",
        icon="mdi:clock-outline",
        value_fn=lambda d: d["reclaimed"]["posted"],
        attr_fn=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MyUsageCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MyUsageSensor(coordinator, description, entry)
        for description in SENSORS
    )


class MyUsageSensor(CoordinatorEntity[MyUsageCoordinator], SensorEntity):
    """A single OUC usage sensor."""

    entity_description: MyUsageSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyUsageCoordinator,
        description: MyUsageSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id    = f"{entry.entry_id}_{description.key}"
        self._attr_device_info  = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name":        "MyUsage",
            "manufacturer":"Exceleron",
            "model":       "MyUsage Portal",
            "entry_type":  "service",
        }

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except (KeyError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.coordinator.data is None or self.entity_description.attr_fn is None:
            return None
        try:
            return self.entity_description.attr_fn(self.coordinator.data)
        except (KeyError, TypeError):
            return None
