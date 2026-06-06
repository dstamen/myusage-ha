"""Sensor platform for OUC MyUsage integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OUCCoordinator

UNIT_GAL = "gal"


@dataclass(frozen=True, kw_only=True)
class OUCSensorDescription(SensorEntityDescription):
    value_fn: callable = None
    attr_fn:  callable = None


SENSORS: tuple[OUCSensorDescription, ...] = (
    OUCSensorDescription(
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
    OUCSensorDescription(
        key="electric_kw",
        name="Electric Peak Demand",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        icon="mdi:flash",
        value_fn=lambda d: d["electric"]["last_kw"],
        attr_fn=None,
    ),
    OUCSensorDescription(
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
    OUCSensorDescription(
        key="reclaimed_gal",
        name="Reclaimed Water",
        native_unit_of_measurement=UNIT_GAL,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water-recycle",
        value_fn=lambda d: d["reclaimed"]["last_gal"],
        attr_fn=lambda d: {
            "posted":  d["reclaimed"]["posted"],
            "type":    d["reclaimed"]["type"],
            "reading": d["reclaimed"]["reading"],
            "meter":   d["meters"]["reclaimed"],
        },
    ),
    OUCSensorDescription(
        key="electric_mtd",
        name="Electric Month-to-Date",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:lightning-bolt-circle",
        value_fn=lambda d: d["electric"]["mtd_kwh"],
        attr_fn=None,
    ),
    OUCSensorDescription(
        key="water_mtd",
        name="Water Month-to-Date",
        native_unit_of_measurement=UNIT_GAL,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water-circle",
        value_fn=lambda d: d["water"]["mtd_gal"],
        attr_fn=None,
    ),
    OUCSensorDescription(
        key="reclaimed_mtd",
        name="Reclaimed Month-to-Date",
        native_unit_of_measurement=UNIT_GAL,
        device_class=SensorDeviceClass.WATER,
        icon="mdi:water-recycle",
        value_fn=lambda d: d["reclaimed"]["mtd_gal"],
        attr_fn=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OUCCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OUCSensor(coordinator, description, entry)
        for description in SENSORS
    )


class OUCSensor(CoordinatorEntity[OUCCoordinator], SensorEntity):
    """A single OUC usage sensor."""

    entity_description: OUCSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OUCCoordinator,
        description: OUCSensorDescription,
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
