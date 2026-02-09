"""The Genial T31 integration."""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_DEVICE_NAME

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Genial T31 integration from YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Genial T31 from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Проверяем, не настроена ли уже эта запись
    if entry.entry_id in hass.data[DOMAIN]:
        _LOGGER.debug("Config entry %s already setup", entry.entry_id)
        return True
    
    from .coordinator import GenialT31Coordinator
    from .ble_client import GenialT31Client
    
    # Create BLE client
    client = GenialT31Client(
        hass=hass,  # Добавлено для работы с Bluetooth proxy
        mac_address=entry.data["mac_address"],
        name=entry.data.get("name", DEFAULT_DEVICE_NAME)
    )
    
    # Create coordinator
    coordinator = GenialT31Coordinator(hass, client)
    
    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Create a callback wrapper that doesn't pass arguments
    def update_callback() -> None:
        """Callback wrapper to trigger coordinator update."""
        # Use hass.loop to schedule the update
        hass.loop.call_soon_threadsafe(
            lambda: hass.async_create_task(coordinator.async_request_refresh())
        )
    
    # Register data callback
    client.set_data_callback(update_callback)
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Немедленно запускаем обновление данных
    await coordinator.async_config_entry_first_refresh()
    
    return True
    
    
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Get coordinator
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator:
            # Disconnect from device
            await coordinator.client.disconnect()
    
    return unload_ok
