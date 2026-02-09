"""Constants for Genial T31 integration."""
from datetime import timedelta
import logging

DOMAIN = "genial_t31"
LOGGER = logging.getLogger(__name__)

CONF_MAC_ADDRESS = "mac_address"
CONF_NAME = "name"

# Таймауты
DATA_TIMEOUT = timedelta(seconds=45)  # 45 секунд без данных = отключение
RECONNECT_INTERVAL = timedelta(seconds=60)  # Переподключение через 60 сек
UPDATE_INTERVAL = timedelta(seconds=30)  # Проверка состояния каждые 30 сек

# BLE UUIDs
SERVICE_UUID = "00001809-0000-1000-8000-00805f9b34fb"
CHAR_TX_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"
CHAR_RX_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"

# Initialization packets
INIT_PACKETS = [
    bytes([0xA6, 0x02, 0xB1, 0x00, 0xB3, 0x6A]),
    bytes([0xA6, 0x02, 0xA5, 0x00, 0xA7, 0x6A]),
    bytes([0xA6, 0x02, 0x1D, 0x00, 0x1F, 0x6A]),
    bytes([0xA6, 0x05, 0x37, 0x03, 0x0B, 0x06, 0x24, 0x74, 0x6A]),
    bytes([0xA6, 0x05, 0x37, 0x03, 0x0B, 0x06, 0x25, 0x75, 0x6A]),
]
