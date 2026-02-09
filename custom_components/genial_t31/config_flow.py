"""Config flow for Genial T31 integration."""
from __future__ import annotations
import re
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    async_discovered_service_info,
)

from .const import DOMAIN, CONF_MAC_ADDRESS, CONF_NAME, SERVICE_UUID

class GenialT31ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Genial T31."""
    
    VERSION = 1
    
    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, str] = {}
        
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfo
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        
        self.context["title_placeholders"] = {
            "name": discovery_info.name,
            "address": discovery_info.address,
        }
        
        self._discovered_devices[discovery_info.address] = discovery_info.name
        
        return await self.async_step_user()
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Validate MAC address
            mac_address = user_input[CONF_MAC_ADDRESS].upper().strip()
            
            if not self._is_valid_mac(mac_address):
                errors[CONF_MAC_ADDRESS] = "invalid_mac"
            else:
                # Set unique ID
                await self.async_set_unique_id(mac_address)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "Genial T31 Thermometer"),
                    data={
                        CONF_MAC_ADDRESS: mac_address,
                        CONF_NAME: user_input.get(CONF_NAME, "Genial T31 Thermometer"),
                    }
                )
        
        # Собираем обнаруженные устройства Bluetooth
        discovered_devices = {}
        
        # Добавляем устройства из шага обнаружения
        discovered_devices.update(self._discovered_devices)
        
        # Также ищем другие устройства через Bluetooth
        for service_info in async_discovered_service_info(self.hass):
            if (
                SERVICE_UUID in service_info.service_uuids
                or "Genial-T31" in service_info.name
            ):
                discovered_devices[service_info.address] = service_info.name
        
        # Если есть обнаруженные устройства, показываем их в списке
        if discovered_devices:
            # Создаем схему с выбором из обнаруженных устройств
            devices = {"": "Ввести вручную"}
            devices.update({addr: f"{name} ({addr})" for addr, name in discovered_devices.items()})
            
            data_schema = vol.Schema({
                vol.Required(CONF_MAC_ADDRESS): vol.In(devices),
                vol.Optional(CONF_NAME, default="Genial T31 Thermometer"): str,
            })
        else:
            # Если устройств не обнаружено, показываем поле для ручного ввода
            data_schema = vol.Schema({
                vol.Required(CONF_MAC_ADDRESS, default=""): str,
                vol.Optional(CONF_NAME, default="Genial T31 Thermometer"): str,
            })
        
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
    
    @staticmethod
    def _is_valid_mac(mac: str) -> bool:
        """Validate MAC address format."""
        # Remove any separators
        mac = mac.replace(":", "").replace("-", "").replace(".", "").upper()
        
        # Check length and characters
        if len(mac) != 12:
            return False
        
        # Check if all characters are hex
        try:
            int(mac, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return GenialT31OptionsFlow(config_entry)


class GenialT31OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Genial T31."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
    
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_NAME,
                    default=self.config_entry.data.get(CONF_NAME, "Genial T31 Thermometer")
                ): str,
            })
        )
