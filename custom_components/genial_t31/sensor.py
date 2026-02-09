"""Sensor platform for Genial T31."""
import logging
from typing import Optional
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_DEVICE_NAME
from .coordinator import GenialT31Coordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "temperature": {
        "unit": "°C",
        "icon": "mdi:thermometer",
        "device_class": "temperature",
        "state_class": "measurement",
    },
    "battery": {
        "unit": "%",
        "icon": "mdi:battery",
        "device_class": "battery",
        "state_class": "measurement",
    },
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Genial T31 sensors from a config entry."""
    coordinator: GenialT31Coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        GenialT31Sensor(coordinator, entry, "temperature"),
        GenialT31Sensor(coordinator, entry, "battery"),
    ]
    
    async_add_entities(sensors)


class GenialT31Sensor(CoordinatorEntity, SensorEntity):
    """Representation of a Genial T31 sensor."""
    
    def __init__(
        self,
        coordinator: GenialT31Coordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._entry = entry
        self._config = SENSOR_TYPES[sensor_type]
        
        self._attr_has_entity_name = True
        self._attr_translation_key = sensor_type
        self._attr_unique_id = f"{entry.unique_id}_{sensor_type}"
        self._attr_device_class = self._config.get("device_class")
        self._attr_native_unit_of_measurement = self._config["unit"]
        self._attr_icon = self._config["icon"]
        self._attr_state_class = self._config["state_class"]
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.data.get("name", DEFAULT_DEVICE_NAME),
            manufacturer="Genial",
            model="T31",
            sw_version="1.0",
        )
        
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Сенсор доступен только если устройство подключено и есть данные
        is_connected = self.coordinator.data.get("connected", False)
        
        if self._sensor_type == "temperature":
            return is_connected and self.native_value is not None
        elif self._sensor_type == "battery":
            return is_connected
        return is_connected
        
    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._sensor_type)
        
    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = {}
        
        # Время последнего обновления
        if last_update := self.coordinator.client.last_update:
            attrs["last_update"] = last_update.isoformat()
        
        # Время последних данных
        if last_data := self.coordinator.data.get("last_data_received"):
            if isinstance(last_data, datetime):
                attrs["last_data_received"] = last_data.isoformat()
            else:
                attrs["last_data_received"] = str(last_data)
        
        # Таймаут данных
        if timeout := self.coordinator.data.get("data_timeout_seconds"):
            attrs["data_timeout_seconds"] = round(timeout, 1)
        
        # Статус подключения
        attrs["connected"] = self.coordinator.data.get("connected", False)
        
        # MAC адрес
        attrs["mac_address"] = self.coordinator.client.mac_address
        
        return attrs
        
    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()