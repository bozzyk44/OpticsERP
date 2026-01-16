# pos_monitor/app/config.py
"""Configuration for POS Monitor"""
import os
from pathlib import Path

# Database
BUFFER_DB_PATH = os.environ.get(
    'BUFFER_DB_PATH',
    str(Path(__file__).parent.parent.parent / 'kkt_adapter' / 'data' / 'buffer.db')
)

# Buffer capacity (from schema.sql)
BUFFER_CAPACITY = 200

# KKT Adapter URL
KKT_ADAPTER_URL = os.environ.get('KKT_ADAPTER_URL', 'http://localhost:8000')

# WebSocket update interval (seconds)
WEBSOCKET_UPDATE_INTERVAL = 2

# Alert thresholds
BUFFER_WARNING_THRESHOLD = 80  # % (160 receipts)
BUFFER_CRITICAL_THRESHOLD = 100  # % (200 receipts)

# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = Path(__file__).parent.parent / 'logs' / 'pos_monitor.log'
