"""
Hybrid Logical Clock (HLC) Implementation

Author: AI Agent
Created: 2025-10-08
Purpose: Generate monotonic timestamps independent of NTP synchronization

Reference:
- CLAUDE.md §4.3
- Lamport, L. (1978) "Time, Clocks and the Ordering of Events"
- Kulkarni et al. (2014) "Logical Physical Clocks"

HLC provides:
1. Monotonic timestamps (never go backwards)
2. Partial ordering of events
3. Independence from NTP drift
4. Thread-safe generation

Structure:
- local_time: Unix timestamp from local system clock
- logical_counter: Monotonic counter for same-second events
- server_time: Assigned during synchronization (optional)

Ordering priority: server_time > local_time > logical_counter
"""

import time
import threading
from dataclasses import dataclass
from typing import Optional


# Global HLC state
_hlc_lock = threading.Lock()
_hlc_counter = 0
_last_hlc_time = 0


@dataclass
class HybridTimestamp:
    """
    Hybrid Logical Clock timestamp

    Attributes:
        local_time: Unix timestamp from local system (seconds since epoch)
        logical_counter: Monotonic counter for ordering within same second
        server_time: Server-assigned timestamp during sync (optional)
    """
    local_time: int
    logical_counter: int
    server_time: Optional[int] = None

    def __lt__(self, other: 'HybridTimestamp') -> bool:
        """
        Comparison operator for ordering

        Priority:
        1. server_time (if present)
        2. local_time
        3. logical_counter

        If one has server_time and other doesn't:
        - Compare server_time vs local_time
        """
        # Determine effective times for comparison
        self_time = self.server_time if self.server_time is not None else self.local_time
        other_time = other.server_time if other.server_time is not None else other.local_time

        # Compare by effective time first
        if self_time != other_time:
            return self_time < other_time

        # If times equal, compare by logical_counter
        return self.logical_counter < other.logical_counter

    def __le__(self, other: 'HybridTimestamp') -> bool:
        """Less than or equal"""
        return self < other or self == other

    def __gt__(self, other: 'HybridTimestamp') -> bool:
        """Greater than"""
        return not self <= other

    def __ge__(self, other: 'HybridTimestamp') -> bool:
        """Greater than or equal"""
        return not self < other

    def __eq__(self, other: object) -> bool:
        """Equality check"""
        if not isinstance(other, HybridTimestamp):
            return NotImplemented

        return (
            self.local_time == other.local_time
            and self.logical_counter == other.logical_counter
            and self.server_time == other.server_time
        )

    def __str__(self) -> str:
        """String representation for debugging"""
        if self.server_time is not None:
            return f"HLC(local={self.local_time}, counter={self.logical_counter}, server={self.server_time})"
        return f"HLC(local={self.local_time}, counter={self.logical_counter})"

    def __repr__(self) -> str:
        """Repr for debugging"""
        return self.__str__()


def generate_hlc() -> HybridTimestamp:
    """
    Generate new Hybrid Logical Clock timestamp

    Thread-safe. Guarantees monotonicity:
    - If called in same second: increments logical_counter
    - If called in new second: resets logical_counter to 0

    Returns:
        HybridTimestamp with local_time and logical_counter
    """
    global _hlc_counter, _last_hlc_time

    with _hlc_lock:
        current_time = int(time.time())

        if current_time == _last_hlc_time:
            # Same second: increment counter
            _hlc_counter += 1
        else:
            # New second: reset counter
            _hlc_counter = 0
            _last_hlc_time = current_time

        return HybridTimestamp(
            local_time=current_time,
            logical_counter=_hlc_counter,
            server_time=None
        )


def update_hlc_on_receive(remote_hlc: HybridTimestamp) -> HybridTimestamp:
    """
    Update HLC when receiving remote timestamp

    Used when receiving events from other nodes (e.g., during sync).
    Ensures local clock advances to at least remote timestamp.

    Algorithm:
    1. local_time' = max(local_time, remote_time, current_time)
    2. If time same as remote: logical_counter' = remote_counter + 1
    3. If time advanced: logical_counter' = 0

    Args:
        remote_hlc: Timestamp received from remote node

    Returns:
        Updated local HybridTimestamp (always > remote_hlc)
    """
    global _hlc_counter, _last_hlc_time

    with _hlc_lock:
        current_time = int(time.time())

        # Compute new local_time: max of local, remote, and current
        new_local_time = max(_last_hlc_time, remote_hlc.local_time, current_time)

        # Determine new counter to ensure monotonicity
        if new_local_time > _last_hlc_time:
            # Time advanced: check if we match remote time
            if new_local_time == remote_hlc.local_time:
                # Same as remote: increment remote's counter
                _hlc_counter = remote_hlc.logical_counter + 1
            else:
                # Advanced past remote: reset counter
                _hlc_counter = 0
        else:
            # Same local time: take max of local and remote counters, then increment
            _hlc_counter = max(_hlc_counter, remote_hlc.logical_counter) + 1

        _last_hlc_time = new_local_time

        return HybridTimestamp(
            local_time=new_local_time,
            logical_counter=_hlc_counter,
            server_time=None
        )


def reset_hlc() -> None:
    """
    Reset HLC state (for testing)

    WARNING: Do not use in production code!
    """
    global _hlc_counter, _last_hlc_time

    with _hlc_lock:
        _hlc_counter = 0
        _last_hlc_time = 0


def assign_server_time(hlc: HybridTimestamp, server_time: int) -> HybridTimestamp:
    """
    Assign server_time to HLC timestamp

    Called during synchronization when server confirms receipt.

    Args:
        hlc: Local HybridTimestamp
        server_time: Server-assigned Unix timestamp

    Returns:
        New HybridTimestamp with server_time assigned
    """
    return HybridTimestamp(
        local_time=hlc.local_time,
        logical_counter=hlc.logical_counter,
        server_time=server_time
    )


# Example usage
if __name__ == "__main__":
    print("=== Hybrid Logical Clock Demo ===\n")

    # Generate timestamps
    print("1. Generating 5 timestamps in quick succession:")
    for i in range(5):
        hlc = generate_hlc()
        print(f"   {i+1}. {hlc}")

    print("\n2. Waiting 1 second...\n")
    time.sleep(1)

    print("3. Generating timestamp after 1s delay:")
    hlc = generate_hlc()
    print(f"   {hlc}")

    print("\n4. Simulating remote timestamp from future:")
    remote = HybridTimestamp(local_time=int(time.time()) + 100, logical_counter=0)
    print(f"   Remote: {remote}")

    updated = update_hlc_on_receive(remote)
    print(f"   Updated local: {updated}")

    print("\n5. Assigning server_time:")
    hlc_with_server = assign_server_time(updated, int(time.time()))
    print(f"   {hlc_with_server}")
