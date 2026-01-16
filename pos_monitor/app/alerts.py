# pos_monitor/app/alerts.py
"""Alert checking logic for POS Monitor"""
import time
import logging
import requests
from typing import List
from .models import Alert
from .database import get_buffer_status
from .config import (
    KKT_ADAPTER_URL,
    BUFFER_WARNING_THRESHOLD,
    BUFFER_CRITICAL_THRESHOLD
)

logger = logging.getLogger(__name__)


def check_alerts() -> List[Alert]:
    """
    Check all alert conditions and return active alerts

    Returns:
        List of Alert objects (P1, P2, INFO)
    """
    alerts = []
    current_time = int(time.time())

    # 1. Buffer overflow alerts
    buffer = get_buffer_status()

    if buffer['percent_full'] >= BUFFER_CRITICAL_THRESHOLD:
        alerts.append(Alert(
            level="P1",
            message=f"Буфер переполнен: {buffer['pending']} чеков ({buffer['percent_full']:.1f}%)",
            action="КРИТИЧНО: Проверьте связь с ОФД. Вызовите техподдержку немедленно.",
            timestamp=current_time
        ))
    elif buffer['percent_full'] >= BUFFER_WARNING_THRESHOLD:
        alerts.append(Alert(
            level="P2",
            message=f"Буфер заполнен: {buffer['pending']} чеков ({buffer['percent_full']:.1f}%)",
            action="ВНИМАНИЕ: Дождитесь синхронизации или проверьте сетевое подключение.",
            timestamp=current_time
        ))

    # 2. DLQ (Dead Letter Queue) alerts
    if buffer['dlq'] > 0:
        alerts.append(Alert(
            level="P1",
            message=f"Ошибки отправки в ОФД: {buffer['dlq']} чеков в DLQ",
            action="КРИТИЧНО: Чеки не отправлены в ОФД после 20 попыток. Вызовите администратора.",
            timestamp=current_time
        ))

    # 3. KKT Adapter offline check
    try:
        response = requests.get(
            f"{KKT_ADAPTER_URL}/health",
            timeout=2
        )
        if response.status_code != 200:
            raise Exception(f"Unhealthy: HTTP {response.status_code}")

    except Exception as e:
        logger.warning(f"KKT Adapter health check failed: {e}")
        alerts.append(Alert(
            level="P1",
            message="ККТ Adapter не отвечает",
            action="КРИТИЧНО: Перезапустите контейнер kkt_adapter или проверьте сервис.",
            timestamp=current_time
        ))

    # 4. OFD offline (Circuit Breaker state)
    try:
        response = requests.get(
            f"{KKT_ADAPTER_URL}/v1/health",
            timeout=2
        )
        if response.status_code == 200:
            health_data = response.json()
            cb_state = health_data.get('circuit_breaker_state', 'UNKNOWN')

            if cb_state == 'OPEN':
                alerts.append(Alert(
                    level="P2",
                    message="ОФД недоступен (Circuit Breaker OPEN)",
                    action="Чеки сохраняются локально. Ожидайте восстановления связи с ОФД.",
                    timestamp=current_time
                ))
            elif cb_state == 'HALF_OPEN':
                alerts.append(Alert(
                    level="INFO",
                    message="ОФД восстанавливается (Circuit Breaker HALF_OPEN)",
                    action="Идёт проверка связи с ОФД. Дождитесь полного восстановления.",
                    timestamp=current_time
                ))

    except Exception as e:
        logger.debug(f"Failed to check Circuit Breaker state: {e}")
        # Not a critical error - KKT Adapter health check will catch offline state

    # 5. Last sync age warning (optional)
    if buffer['last_sync']:
        time_since_sync = current_time - buffer['last_sync']
        hours_since_sync = time_since_sync / 3600

        if hours_since_sync > 2 and buffer['pending'] > 0:
            alerts.append(Alert(
                level="P2",
                message=f"Последняя синхронизация {hours_since_sync:.1f} часов назад",
                action="Проверьте сетевое подключение и состояние ОФД.",
                timestamp=current_time
            ))

    return alerts


def get_kkt_status() -> dict:
    """
    Get KKT Adapter status from health endpoint

    Returns:
        Dict with is_online, circuit_breaker_state, ofd_status, last_heartbeat
    """
    current_time = int(time.time())

    try:
        # Check basic health
        health_response = requests.get(
            f"{KKT_ADAPTER_URL}/health",
            timeout=2
        )
        is_online = (health_response.status_code == 200)

        # Get detailed health (Circuit Breaker state)
        detailed_response = requests.get(
            f"{KKT_ADAPTER_URL}/v1/health",
            timeout=2
        )

        if detailed_response.status_code == 200:
            health_data = detailed_response.json()
            cb_state = health_data.get('circuit_breaker_state', 'UNKNOWN')
            ofd_status = 'offline' if cb_state == 'OPEN' else 'online'
        else:
            cb_state = 'UNKNOWN'
            ofd_status = 'unknown'

        return {
            "is_online": is_online,
            "circuit_breaker_state": cb_state,
            "last_heartbeat": current_time,
            "ofd_status": ofd_status
        }

    except Exception as e:
        logger.error(f"Failed to get KKT status: {e}")
        return {
            "is_online": False,
            "circuit_breaker_state": "UNKNOWN",
            "last_heartbeat": current_time,
            "ofd_status": "unknown"
        }
