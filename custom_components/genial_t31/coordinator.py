"""Data coordinator for Genial T31."""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL, RECONNECT_INTERVAL

class GenialT31Coordinator(DataUpdateCoordinator):
    """Coordinator for Genial T31 device."""
    
    def __init__(self, hass: HomeAssistant, client) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.data: Dict[str, Any] = {
            "temperature": None,
            "battery": None,
            "connected": False,
            "last_data_received": None,
            "data_timeout_seconds": None,
        }
        self._last_connection_attempt = 0
        
    async def _async_update_data(self) -> Dict[str, Any]:
        """Update device data."""
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Проверяем таймаут данных
            if self.client.check_data_timeout():
                LOGGER.debug("Таймаут данных: %.1f сек", self.client.data_timeout_seconds)
                self.data["connected"] = False
                self.data["data_timeout_seconds"] = self.client.data_timeout_seconds
                
                # Пытаемся переподключиться
                if (current_time - self._last_connection_attempt) > RECONNECT_INTERVAL.total_seconds():
                    LOGGER.info("Попытка переподключения")
                    await self.client.disconnect()
                    await self.client.connect()
                    self._last_connection_attempt = current_time
                
                return self.data
            
            # Если устройство не подключено, пытаемся подключиться
            if not self.client.connected:
                LOGGER.debug("Устройство не подключено")
                
                if (current_time - self._last_connection_attempt) > RECONNECT_INTERVAL.total_seconds():
                    await self.client.connect()
                    self._last_connection_attempt = current_time
            
            # Обновляем данные
            self.data.update({
                "temperature": self.client.temperature,
                "battery": self.client.battery,
                "connected": self.client.connected,
                "last_data_received": self.client.last_data_received,
                "data_timeout_seconds": self.client.data_timeout_seconds,
            })
            
            return self.data
            
        except Exception as err:
            LOGGER.error("Ошибка обновления: %s", err)
            self.data["connected"] = False
            return self.data