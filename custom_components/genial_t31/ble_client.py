"""BLE client for Genial T31."""
import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime, timedelta

from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components.bluetooth import (
    async_get_scanner,
    async_ble_device_from_address,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)

from .const import (
    LOGGER,
    SERVICE_UUID,
    CHAR_TX_UUID,
    CHAR_RX_UUID,
    INIT_PACKETS,
    DATA_TIMEOUT,
)

class GenialT31Client:
    """BLE client for Genial T31 thermometer."""
    
    def __init__(self, hass, mac_address: str, name: str) -> None:
        """Initialize the client."""
        self.hass = hass
        self.mac_address = mac_address
        self.name = name
        self.client: Optional[BleakClient] = None
        self._connected = False
        self._temperature: Optional[float] = None
        self._battery: Optional[int] = None
        self._last_data_received: Optional[datetime] = None
        self._last_update: Optional[datetime] = None
        self._data_callback: Optional[Callable[[], None]] = None
        self._notification_enabled = False
        self._scanner = None
        
    async def connect(self) -> bool:
        """Connect to the device using Bluetooth proxy."""
        try:
            LOGGER.info("Подключение к %s через Bluetooth proxy", self.name)
            
            # Получаем устройство через Bluetooth интеграцию (работает с proxy)
            device = await self._get_ble_device()
            if not device:
                LOGGER.error("Устройство не найдено через Bluetooth proxy")
                return False
            
            # Используем establish_connection для автоматического переподключения
            # Этот метод поддерживает Bluetooth proxy через bleak-retry-connector
            self.client = await establish_connection(
                client_class=BleakClient,
                device=device,
                name=self.name,
                disconnected_callback=self._handle_disconnect,
                max_attempts=2,
                use_services_cache=True,
            )
            
            if not self.client or not self.client.is_connected:
                LOGGER.error("Соединение не установлено")
                return False
            
            LOGGER.info("✅ Соединение установлено через Bluetooth proxy")
            
            # Включаем уведомления
            await self.client.start_notify(CHAR_RX_UUID, self._notification_handler)
            self._notification_enabled = True
            
            # Ждем немного перед отправкой пакетов
            await asyncio.sleep(0.5)
            
            # Отправляем пакеты инициализации
            await self._send_init_packets()
            
            self._connected = True
            self._last_data_received = datetime.now()
            
            return True
            
        except Exception as err:
            LOGGER.error("Ошибка подключения через Bluetooth proxy: %s", err)
            self._connected = False
            return False
    
    async def _get_ble_device(self):
        """Get BLE device using Bluetooth proxy."""
        try:
            # Используем Home Assistant Bluetooth API для получения устройства
            # Это работает с Bluetooth proxy
            scanner = async_get_scanner(self.hass)
            if not scanner:
                LOGGER.error("Bluetooth scanner не найден")
                return None
            
            # Ищем устройство по MAC адресу
            device = async_ble_device_from_address(
                self.hass, 
                self.mac_address.upper(), 
                connectable=True
            )
            
            if device:
                LOGGER.debug("Устройство найдено через Bluetooth API")
                return device
            
            # Если не найдено, пытаемся получить через сканер
            LOGGER.debug("Сканируем для поиска устройства...")
            
            # Используем сканер для поиска устройства
            # Это нужно, если устройство еще не было обнаружено
            discovered_devices = scanner.discovered_devices
            
            for dev in discovered_devices:
                if dev.address.upper() == self.mac_address.upper():
                    LOGGER.debug("Устройство найдено при сканировании")
                    return dev
            
            LOGGER.error("Устройство не найдено при сканировании")
            return None
            
        except Exception as err:
            LOGGER.error("Ошибка получения устройства через Bluetooth proxy: %s", err)
            return None
    
    async def _send_init_packets(self) -> None:
        """Send initialization packets."""
        if not self.client or not self.client.is_connected:
            return
        
        try:
            LOGGER.debug("Отправка пакетов инициализации")
            
            for i, packet in enumerate(INIT_PACKETS, 1):
                try:
                    await self.client.write_gatt_char(CHAR_TX_UUID, packet)
                    await asyncio.sleep(1)
                except Exception as e:
                    LOGGER.error("Ошибка отправки пакета %d: %s", i, e)
            
        except Exception as err:
            LOGGER.error("Ошибка отправки пакетов: %s", err)
    
    def _notification_handler(self, sender: str, data: bytearray) -> None:
        """Handle incoming notifications."""
        try:
            # Обновляем время последних данных
            self._last_data_received = datetime.now()
            
            # Обработка данных
            if len(data) == 13:
                # Пакет с температурой
                temp_raw = (data[3] << 8) | data[4]
                temperature = temp_raw / 100.0
                
                if 20.0 <= temperature <= 45.0:
                    self._temperature = temperature
                
            elif len(data) == 9:
                # Пакет с батареей
                if len(data) >= 7:
                    charge_raw = (data[5] << 8) | data[6]
                    battery_voltage = charge_raw / 100.0
                    
                    # Расчет процента батареи
                    min_voltage = 2.0
                    max_voltage = 2.45
                    battery_percent = (battery_voltage - min_voltage) / (max_voltage - min_voltage) * 100.0
                    battery_percent = max(0, min(100, battery_percent))
                    
                    self._battery = int(battery_percent)
            
            self._last_update = datetime.now()
            
            # Уведомляем координатор
            if self._data_callback:
                self._data_callback()
                
        except Exception as err:
            LOGGER.error("Ошибка обработки уведомления: %s", err)
    
    def _handle_disconnect(self, client: BleakClient) -> None:
        """Handle disconnect event."""
        LOGGER.warning("Устройство отключилось")
        self._connected = False
        self._notification_enabled = False
        
    async def disconnect(self) -> None:
        """Disconnect from the device."""
        if self.client:
            try:
                if self._notification_enabled and self.client.is_connected:
                    await self.client.stop_notify(CHAR_RX_UUID)
                
                if self.client.is_connected:
                    await self.client.disconnect()
                
            except Exception:
                pass
            finally:
                self._connected = False
                self._notification_enabled = False
                self.client = None
    
    def check_data_timeout(self) -> bool:
        """Check if data reception has timed out."""
        if not self._last_data_received:
            return True
        
        time_since_last_data = datetime.now() - self._last_data_received
        return time_since_last_data > DATA_TIMEOUT
    
    def set_data_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for data updates."""
        self._data_callback = callback
        
    @property
    def connected(self) -> bool:
        """Return connection status."""
        if not self.client or not self.client.is_connected:
            return False
        
        return not self.check_data_timeout()
        
    @property
    def temperature(self) -> Optional[float]:
        """Return current temperature."""
        return self._temperature
        
    @property
    def battery(self) -> Optional[int]:
        """Return current battery level."""
        return self._battery
        
    @property
    def last_update(self) -> Optional[datetime]:
        """Return last update time."""
        return self._last_update
        
    @property
    def last_data_received(self) -> Optional[datetime]:
        """Return last data reception time."""
        return self._last_data_received
        
    @property
    def data_timeout_seconds(self) -> float:
        """Return seconds since last data."""
        if not self._last_data_received:
            return float('inf')
        
        return (datetime.now() - self._last_data_received).total_seconds()
