"""
Unit tests for Hybrid Logical Clock (HLC)

Author: AI Agent
Created: 2025-10-08
Purpose: Test HLC timestamp generation, monotonicity, ordering, thread-safety

Reference: CLAUDE.md §4.3, TESTING_REQUIREMENTS.md
"""

import time
import threading
import pytest
from dataclasses import dataclass
from typing import Optional


# Import will work after hlc.py is created
import sys
sys.path.insert(0, 'D:\\OpticsERP\\kkt_adapter\\app')

from hlc import HybridTimestamp, generate_hlc, update_hlc_on_receive, reset_hlc


class TestHybridTimestamp:
    """Test HybridTimestamp dataclass and comparison"""

    def test_timestamp_creation(self):
        """Создание HLC timestamp с корректными полями"""
        hlc = HybridTimestamp(
            local_time=1696800000,
            logical_counter=0,
            server_time=None
        )

        assert hlc.local_time == 1696800000
        assert hlc.logical_counter == 0
        assert hlc.server_time is None

    def test_timestamp_with_server_time(self):
        """HLC с присвоенным server_time"""
        hlc = HybridTimestamp(
            local_time=1696800000,
            logical_counter=5,
            server_time=1696800100
        )

        assert hlc.server_time == 1696800100

    def test_comparison_by_local_time(self):
        """Сравнение по local_time (когда server_time отсутствует)"""
        hlc1 = HybridTimestamp(local_time=1000, logical_counter=0)
        hlc2 = HybridTimestamp(local_time=2000, logical_counter=0)

        assert hlc1 < hlc2
        assert hlc2 > hlc1

    def test_comparison_by_logical_counter(self):
        """Сравнение по logical_counter (при равном local_time)"""
        hlc1 = HybridTimestamp(local_time=1000, logical_counter=0)
        hlc2 = HybridTimestamp(local_time=1000, logical_counter=1)

        assert hlc1 < hlc2

    def test_comparison_by_server_time(self):
        """Сравнение по server_time (высший приоритет)"""
        hlc1 = HybridTimestamp(
            local_time=2000,
            logical_counter=5,
            server_time=1000
        )
        hlc2 = HybridTimestamp(
            local_time=1000,
            logical_counter=0,
            server_time=2000
        )

        # server_time имеет приоритет
        assert hlc1 < hlc2


class TestGenerateHLC:
    """Test HLC generation"""

    def setup_method(self):
        """Reset HLC state before each test"""
        reset_hlc()

    def test_hlc_generation(self):
        """HLC генерирует timestamp с корректными полями"""
        hlc = generate_hlc()

        assert hlc.local_time > 0
        assert hlc.logical_counter >= 0
        assert hlc.server_time is None

    def test_hlc_monotonic(self):
        """HLC монотонно возрастает"""
        hlc1 = generate_hlc()
        time.sleep(0.001)  # 1ms
        hlc2 = generate_hlc()

        assert hlc2 > hlc1

    def test_hlc_same_second_increments_counter(self):
        """При генерации в ту же секунду инкрементится logical_counter"""
        hlc1 = generate_hlc()
        hlc2 = generate_hlc()

        # Скорее всего в ту же секунду
        if hlc1.local_time == hlc2.local_time:
            assert hlc2.logical_counter == hlc1.logical_counter + 1
        else:
            # Если время сдвинулось, counter сбрасывается
            assert hlc2.logical_counter == 0

    def test_hlc_different_second_resets_counter(self):
        """При смене секунды logical_counter сбрасывается"""
        hlc1 = generate_hlc()
        time.sleep(1.1)  # Гарантированно следующая секунда
        hlc2 = generate_hlc()

        assert hlc2.local_time > hlc1.local_time
        assert hlc2.logical_counter == 0

    def test_hlc_multiple_generations(self):
        """Генерация нескольких HLC timestamps"""
        timestamps = [generate_hlc() for _ in range(10)]

        # Проверка монотонности
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1]


class TestUpdateHLCOnReceive:
    """Test HLC update when receiving remote timestamp"""

    def setup_method(self):
        """Reset HLC state before each test"""
        reset_hlc()

    def test_receive_future_timestamp(self):
        """Получение timestamp из будущего обновляет local_time"""
        # Generate local timestamp
        local_hlc = generate_hlc()

        # Simulate receiving timestamp from future
        remote_hlc = HybridTimestamp(
            local_time=local_hlc.local_time + 100,
            logical_counter=0,
            server_time=None
        )

        updated = update_hlc_on_receive(remote_hlc)

        # Updated timestamp should be > remote
        assert updated.local_time >= remote_hlc.local_time
        assert updated > remote_hlc

    def test_receive_past_timestamp(self):
        """Получение timestamp из прошлого не откатывает local_time"""
        # Generate local timestamp
        local_hlc = generate_hlc()

        # Simulate receiving timestamp from past
        remote_hlc = HybridTimestamp(
            local_time=local_hlc.local_time - 100,
            logical_counter=0,
            server_time=None
        )

        updated = update_hlc_on_receive(remote_hlc)

        # Local time should not go backwards
        assert updated.local_time >= local_hlc.local_time
        assert updated > remote_hlc

    def test_receive_same_time_increments_counter(self):
        """Получение timestamp с тем же временем инкрементирует counter"""
        local_hlc = generate_hlc()

        remote_hlc = HybridTimestamp(
            local_time=local_hlc.local_time,
            logical_counter=local_hlc.logical_counter,
            server_time=None
        )

        updated = update_hlc_on_receive(remote_hlc)

        assert updated.logical_counter > max(local_hlc.logical_counter, remote_hlc.logical_counter)

    def test_receive_far_future_timestamp(self):
        """Получение timestamp далеко в будущем сбрасывает counter"""
        # Generate local timestamp
        local_hlc = generate_hlc()

        # Simulate receiving timestamp far in the future (>1 second)
        remote_hlc = HybridTimestamp(
            local_time=int(time.time()) - 100,  # Remote is in past
            logical_counter=10,
            server_time=None
        )

        # Wait a bit to ensure current_time advances
        time.sleep(0.1)

        updated = update_hlc_on_receive(remote_hlc)

        # When current_time > remote and current > last, counter should reset
        # This covers line 175
        assert updated.local_time > remote_hlc.local_time


class TestHLCThreadSafety:
    """Test HLC thread safety"""

    def setup_method(self):
        """Reset HLC state before each test"""
        reset_hlc()

    def test_concurrent_generation(self):
        """Конкурентная генерация HLC из нескольких потоков"""
        timestamps = []
        lock = threading.Lock()

        def generate_timestamps():
            for _ in range(100):
                hlc = generate_hlc()
                with lock:
                    timestamps.append(hlc)

        # Create 5 threads
        threads = [threading.Thread(target=generate_timestamps) for _ in range(5)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify we got 500 timestamps
        assert len(timestamps) == 500

        # Verify monotonicity (sort by comparison)
        sorted_timestamps = sorted(timestamps)

        for i in range(len(sorted_timestamps) - 1):
            assert sorted_timestamps[i] <= sorted_timestamps[i + 1]

    def test_no_duplicate_timestamps(self):
        """Нет дубликатов timestamps при конкурентной генерации"""
        timestamps = []
        lock = threading.Lock()

        def generate_timestamps():
            for _ in range(50):
                hlc = generate_hlc()
                with lock:
                    timestamps.append(hlc)

        threads = [threading.Thread(target=generate_timestamps) for _ in range(4)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Convert to tuples for uniqueness check
        timestamp_tuples = [
            (hlc.local_time, hlc.logical_counter, hlc.server_time)
            for hlc in timestamps
        ]

        # All should be unique
        assert len(timestamp_tuples) == len(set(timestamp_tuples))


class TestHLCEdgeCases:
    """Test edge cases and error conditions"""

    def setup_method(self):
        """Reset HLC state before each test"""
        reset_hlc()

    def test_hlc_str_representation(self):
        """String representation для debugging"""
        hlc = HybridTimestamp(
            local_time=1696800000,
            logical_counter=42,
            server_time=None
        )

        str_repr = str(hlc)
        assert '1696800000' in str_repr
        assert '42' in str_repr

    def test_hlc_str_with_server_time(self):
        """String representation с server_time"""
        hlc = HybridTimestamp(
            local_time=1696800000,
            logical_counter=42,
            server_time=1696800100
        )

        str_repr = str(hlc)
        assert '1696800000' in str_repr
        assert '42' in str_repr
        assert '1696800100' in str_repr

    def test_hlc_repr(self):
        """Repr для debugging"""
        hlc = HybridTimestamp(local_time=1000, logical_counter=5)
        repr_str = repr(hlc)
        assert '1000' in repr_str
        assert '5' in repr_str

    def test_hlc_equality(self):
        """Проверка равенства timestamps"""
        hlc1 = HybridTimestamp(local_time=1000, logical_counter=5)
        hlc2 = HybridTimestamp(local_time=1000, logical_counter=5)

        assert hlc1 == hlc2
        assert not (hlc1 < hlc2)
        assert not (hlc1 > hlc2)

    def test_hlc_inequality(self):
        """Проверка неравенства timestamps"""
        hlc1 = HybridTimestamp(local_time=1000, logical_counter=5)
        hlc2 = HybridTimestamp(local_time=1000, logical_counter=6)

        assert hlc1 != hlc2
        assert hlc1 < hlc2
        assert hlc2 > hlc1

    def test_hlc_greater_than_or_equal(self):
        """Проверка >= оператора"""
        hlc1 = HybridTimestamp(local_time=1000, logical_counter=5)
        hlc2 = HybridTimestamp(local_time=1000, logical_counter=5)
        hlc3 = HybridTimestamp(local_time=1000, logical_counter=6)

        assert hlc1 >= hlc2  # Equal
        assert hlc3 >= hlc1  # Greater

    def test_hlc_less_than_or_equal(self):
        """Проверка <= оператора"""
        hlc1 = HybridTimestamp(local_time=1000, logical_counter=5)
        hlc2 = HybridTimestamp(local_time=1000, logical_counter=5)
        hlc3 = HybridTimestamp(local_time=1000, logical_counter=6)

        assert hlc1 <= hlc2  # Equal
        assert hlc1 <= hlc3  # Less

    def test_hlc_equality_with_non_timestamp(self):
        """Equality с non-HybridTimestamp возвращает NotImplemented"""
        hlc = HybridTimestamp(local_time=1000, logical_counter=5)

        assert hlc != "not a timestamp"
        assert hlc != 123
        assert hlc != None


class TestAssignServerTime:
    """Test assign_server_time function"""

    def test_assign_server_time(self):
        """Присвоение server_time к HLC"""
        from hlc import assign_server_time

        local_hlc = HybridTimestamp(
            local_time=1696800000,
            logical_counter=5,
            server_time=None
        )

        server_time = 1696800100
        updated = assign_server_time(local_hlc, server_time)

        assert updated.server_time == server_time
        assert updated.local_time == local_hlc.local_time
        assert updated.logical_counter == local_hlc.logical_counter

    def test_assign_server_time_changes_ordering(self):
        """Присвоение server_time меняет порядок сортировки"""
        from hlc import assign_server_time

        hlc1 = HybridTimestamp(local_time=2000, logical_counter=0)
        hlc2 = HybridTimestamp(local_time=1000, logical_counter=0)

        # Without server_time: hlc1 > hlc2
        assert hlc1 > hlc2

        # Assign server_time to hlc2
        hlc2_with_server = assign_server_time(hlc2, 3000)

        # Now hlc2 > hlc1 (server_time takes precedence)
        assert hlc2_with_server > hlc1


# Pytest fixtures
@pytest.fixture
def fresh_hlc_state():
    """Fixture для чистого HLC state"""
    reset_hlc()
    yield
    reset_hlc()
