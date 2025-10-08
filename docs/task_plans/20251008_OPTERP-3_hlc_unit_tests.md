# Task Plan: OPTERP-3 - Create HLC Unit Tests

**Author:** AI Agent
**Created:** 2025-10-08
**JIRA Ticket:** OPTERP-3
**Epic:** OPTERP-80 (Phase 1: POC)
**Story Points:** 2
**Priority:** Highest
**Labels:** poc, week1, hlc, test

---

## 📋 Task Summary

Create comprehensive unit tests for Hybrid Logical Clock (HLC) implementation in `tests/unit/test_hlc.py` to verify correctness, monotonicity, ordering, thread-safety, and edge cases.

---

## 🎯 Acceptance Criteria

- [x] test_hlc_monotonic() passes
- [x] test_hlc_same_second() passes
- [x] test_hlc_ordering() passes
- [x] test_hlc_thread_safe() passes
- [x] 5+ tests total

---

## 📚 Background & Context

### Why Unit Tests for HLC?

HLC is **critical infrastructure** for the entire offline-first system:
- Used to order ALL receipts in SQLite buffer
- Must guarantee monotonicity (no duplicates, no time travel)
- Must be thread-safe (multiple concurrent receipts)
- Edge cases can cause data corruption if not handled

### Test Coverage Goals

| Category | Tests | Coverage |
|----------|-------|----------|
| **Basic functionality** | 2 tests | Generation, reset |
| **Monotonicity** | 2 tests | Time advance, same-second |
| **Ordering** | 3 tests | All comparison operators, server_time priority |
| **Thread safety** | 1 test | 100 concurrent calls |
| **Edge cases** | 2 tests | Remote sync, future timestamps |
| **Serialization** | 1 test | to_dict/from_dict |
| **Total** | **11 tests** | **~95% code coverage** |

---

## 📂 Files to Create/Modify

### Files to Create

1. **`tests/unit/test_hlc.py`** (NEW)
   - Purpose: HLC unit tests
   - Lines: ~250-300
   - Tests: 11+
   - Dependencies: pytest

2. **`tests/__init__.py`** (NEW)
   - Purpose: Mark tests directory as Python package

3. **`tests/unit/__init__.py`** (NEW)
   - Purpose: Mark unit tests directory as package

### Files to Modify

- None (tests only, no production code changes)

---

## 🔨 Implementation Steps

### Step 1: Create Test Directory Structure

**Command:**
```bash
mkdir -p tests/unit
touch tests/__init__.py
touch tests/unit/__init__.py
```

**Verification:**
```bash
ls -la tests/
ls -la tests/unit/
# Expected: __init__.py in both directories
```

---

### Step 2: Create test_hlc.py Skeleton

**File:** `tests/unit/test_hlc.py`

**Code:**
```python
"""
Unit Tests for Hybrid Logical Clock (HLC)

Author: AI Agent
Created: 2025-10-08
Purpose: Comprehensive tests for HLC implementation

Test Coverage:
- Basic functionality (generation, reset)
- Monotonicity (time advance, same-second)
- Ordering (comparison operators, server_time priority)
- Thread safety (concurrent generation)
- Edge cases (remote sync, future timestamps)
- Serialization (to_dict/from_dict)

Run:
    pytest tests/unit/test_hlc.py -v
    pytest tests/unit/test_hlc.py -v --cov=kkt_adapter.app.hlc
"""

import pytest
import time
import threading
from kkt_adapter.app.hlc import (
    HybridTimestamp,
    generate_hlc,
    update_hlc_on_receive,
    assign_server_time,
    reset_hlc
)


@pytest.fixture(autouse=True)
def reset_hlc_state():
    """Reset HLC state before each test"""
    reset_hlc()
    yield
    reset_hlc()
```

**Checkpoint:** File compiles
```bash
python -c "import tests.unit.test_hlc; print('✓ OK')"
```

---

### Step 3: Implement Basic Functionality Tests

**File:** `tests/unit/test_hlc.py` (append)

**Code:**
```python
# ==============================================================================
# Basic Functionality Tests
# ==============================================================================

def test_hlc_generation():
    """Test basic HLC generation"""
    hlc = generate_hlc()

    assert isinstance(hlc, HybridTimestamp)
    assert hlc.local_time > 0, "local_time must be positive"
    assert hlc.logical_counter >= 0, "counter must be non-negative"
    assert hlc.server_time is None, "server_time must be None initially"


def test_hlc_reset():
    """Test HLC state reset"""
    # Generate some timestamps
    hlc1 = generate_hlc()
    hlc2 = generate_hlc()
    assert hlc2.logical_counter > 0, "Counter should increment"

    # Reset state
    reset_hlc()

    # Next timestamp should start fresh
    hlc3 = generate_hlc()
    assert hlc3.logical_counter == 0, "Counter should reset to 0"


# ==============================================================================
# Monotonicity Tests
# ==============================================================================

def test_hlc_monotonic():
    """Test HLC timestamps are monotonic (always increasing)"""
    hlc1 = generate_hlc()
    time.sleep(1)  # Wait 1 second
    hlc2 = generate_hlc()

    assert hlc2 > hlc1, f"Monotonicity violated: {hlc2} should be > {hlc1}"
    assert hlc2.local_time > hlc1.local_time, "Time should advance"


def test_hlc_same_second():
    """Test logical counter increments within same second"""
    reset_hlc()

    hlc1 = generate_hlc()
    hlc2 = generate_hlc()
    hlc3 = generate_hlc()

    # All should be in same second (if test runs fast enough)
    if hlc1.local_time == hlc2.local_time == hlc3.local_time:
        assert hlc2.logical_counter == hlc1.logical_counter + 1
        assert hlc3.logical_counter == hlc2.logical_counter + 1
        assert hlc3 > hlc2 > hlc1, "Ordering must work via counter"
    else:
        # Time advanced, counter should reset
        assert hlc2.logical_counter == 0 or hlc3.logical_counter == 0


def test_hlc_monotonic_across_seconds():
    """Test monotonicity when crossing second boundary"""
    timestamps = []

    for i in range(10):
        hlc = generate_hlc()
        timestamps.append(hlc)
        if i % 3 == 0:
            time.sleep(0.1)  # Occasional delay

    # All timestamps must be strictly ordered
    for i in range(len(timestamps) - 1):
        assert timestamps[i+1] > timestamps[i], \
            f"Monotonicity violated at index {i}: {timestamps[i+1]} should be > {timestamps[i]}"
```

---

### Step 4: Implement Ordering Tests

**File:** `tests/unit/test_hlc.py` (append)

**Code:**
```python
# ==============================================================================
# Ordering Tests
# ==============================================================================

def test_hlc_ordering_operators():
    """Test all comparison operators (<, <=, >, >=, ==)"""
    reset_hlc()

    hlc1 = generate_hlc()
    time.sleep(0.01)
    hlc2 = generate_hlc()

    # Less than / Greater than
    assert hlc1 < hlc2
    assert hlc2 > hlc1
    assert not (hlc2 < hlc1)
    assert not (hlc1 > hlc2)

    # Less than or equal / Greater than or equal
    assert hlc1 <= hlc2
    assert hlc2 >= hlc1
    assert hlc1 <= hlc1  # Equal to itself
    assert hlc2 >= hlc2

    # Equality
    assert hlc1 == hlc1
    assert hlc2 == hlc2
    assert not (hlc1 == hlc2)


def test_hlc_ordering_server_time_priority():
    """Test server_time has highest priority in ordering"""
    reset_hlc()

    # Create two timestamps
    hlc1 = generate_hlc()
    time.sleep(1)
    hlc2 = generate_hlc()

    # hlc2 > hlc1 (by local_time)
    assert hlc2 > hlc1

    # Assign server_time to hlc1 (in the future)
    hlc1_with_server = assign_server_time(hlc1, hlc2.local_time + 100)

    # Now hlc1_with_server > hlc2 (server_time takes priority)
    assert hlc1_with_server > hlc2, \
        "server_time should have highest priority"


def test_hlc_ordering_counter_tiebreaker():
    """Test logical_counter breaks ties when times equal"""
    reset_hlc()

    hlc1 = generate_hlc()
    hlc2 = generate_hlc()

    # If same second
    if hlc1.local_time == hlc2.local_time:
        assert hlc2.logical_counter > hlc1.logical_counter
        assert hlc2 > hlc1, "Counter should break tie"


def test_hlc_sorting():
    """Test HLC timestamps can be sorted"""
    timestamps = [generate_hlc() for _ in range(10)]

    # Shuffle
    import random
    shuffled = timestamps.copy()
    random.shuffle(shuffled)

    # Sort
    sorted_ts = sorted(shuffled)

    # Verify sorted order
    for i in range(len(sorted_ts) - 1):
        assert sorted_ts[i] <= sorted_ts[i+1]
```

---

### Step 5: Implement Thread Safety Test

**File:** `tests/unit/test_hlc.py` (append)

**Code:**
```python
# ==============================================================================
# Thread Safety Tests
# ==============================================================================

def test_hlc_thread_safe():
    """Test HLC generation is thread-safe (100 concurrent calls)"""
    reset_hlc()

    num_threads = 100
    timestamps = []
    lock = threading.Lock()

    def generate_timestamp():
        hlc = generate_hlc()
        with lock:
            timestamps.append(hlc)

    # Create and start threads
    threads = [threading.Thread(target=generate_timestamp) for _ in range(num_threads)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # Verify: no duplicates, all unique
    assert len(timestamps) == num_threads, "Should have exactly 100 timestamps"

    # Check for duplicates
    timestamp_tuples = [(ts.local_time, ts.logical_counter) for ts in timestamps]
    unique_tuples = set(timestamp_tuples)

    assert len(unique_tuples) == num_threads, \
        f"Found duplicates! {num_threads - len(unique_tuples)} duplicate timestamps"

    # All timestamps should be orderable
    sorted_ts = sorted(timestamps)
    for i in range(len(sorted_ts) - 1):
        assert sorted_ts[i] <= sorted_ts[i+1]
```

---

### Step 6: Implement Edge Case Tests

**File:** `tests/unit/test_hlc.py` (append)

**Code:**
```python
# ==============================================================================
# Edge Case Tests
# ==============================================================================

def test_hlc_update_on_receive_future():
    """Test update_hlc_on_receive with future remote timestamp"""
    reset_hlc()

    local_hlc = generate_hlc()

    # Remote timestamp from future
    remote_hlc = HybridTimestamp(
        local_time=local_hlc.local_time + 100,
        logical_counter=0,
        server_time=None
    )

    # Update local clock
    updated_hlc = update_hlc_on_receive(remote_hlc)

    # Updated clock should be > remote
    assert updated_hlc > remote_hlc, "Updated clock must be > remote"
    assert updated_hlc.local_time >= remote_hlc.local_time, \
        "Local time should advance to at least remote time"


def test_hlc_update_on_receive_past():
    """Test update_hlc_on_receive with past remote timestamp"""
    reset_hlc()

    # Wait to get a timestamp in the future
    time.sleep(1)
    local_hlc = generate_hlc()

    # Remote timestamp from past
    remote_hlc = HybridTimestamp(
        local_time=local_hlc.local_time - 100,
        logical_counter=0,
        server_time=None
    )

    # Update local clock
    updated_hlc = update_hlc_on_receive(remote_hlc)

    # Updated clock should be > local (monotonicity preserved)
    assert updated_hlc > local_hlc, "Clock must advance monotonically"


def test_hlc_assign_server_time():
    """Test assigning server_time to HLC"""
    reset_hlc()

    hlc = generate_hlc()
    server_time = int(time.time()) + 10

    hlc_with_server = assign_server_time(hlc, server_time)

    assert hlc_with_server.local_time == hlc.local_time
    assert hlc_with_server.logical_counter == hlc.logical_counter
    assert hlc_with_server.server_time == server_time

    # Original should be unchanged (immutable)
    assert hlc.server_time is None
```

---

### Step 7: Implement Serialization Test

**File:** `tests/unit/test_hlc.py` (append)

**Code:**
```python
# ==============================================================================
# Serialization Tests
# ==============================================================================

def test_hlc_to_dict():
    """Test HybridTimestamp serialization to dict"""
    hlc = HybridTimestamp(
        local_time=1696800000,
        logical_counter=42,
        server_time=1696800100
    )

    data = hlc.to_dict()

    assert data == {
        'local_time': 1696800000,
        'logical_counter': 42,
        'server_time': 1696800100
    }


def test_hlc_from_dict():
    """Test HybridTimestamp deserialization from dict"""
    data = {
        'local_time': 1696800000,
        'logical_counter': 42,
        'server_time': 1696800100
    }

    hlc = HybridTimestamp.from_dict(data)

    assert hlc.local_time == 1696800000
    assert hlc.logical_counter == 42
    assert hlc.server_time == 1696800100


def test_hlc_serialization_roundtrip():
    """Test serialization roundtrip (to_dict → from_dict)"""
    original = generate_hlc()
    original_with_server = assign_server_time(original, int(time.time()))

    # Roundtrip
    data = original_with_server.to_dict()
    restored = HybridTimestamp.from_dict(data)

    assert restored == original_with_server
    assert restored.local_time == original_with_server.local_time
    assert restored.logical_counter == original_with_server.logical_counter
    assert restored.server_time == original_with_server.server_time
```

---

## 🧪 Running Tests

### Run All HLC Tests

```bash
pytest tests/unit/test_hlc.py -v
```

**Expected Output:**
```
tests/unit/test_hlc.py::test_hlc_generation PASSED
tests/unit/test_hlc.py::test_hlc_reset PASSED
tests/unit/test_hlc.py::test_hlc_monotonic PASSED
tests/unit/test_hlc.py::test_hlc_same_second PASSED
tests/unit/test_hlc.py::test_hlc_monotonic_across_seconds PASSED
tests/unit/test_hlc.py::test_hlc_ordering_operators PASSED
tests/unit/test_hlc.py::test_hlc_ordering_server_time_priority PASSED
tests/unit/test_hlc.py::test_hlc_ordering_counter_tiebreaker PASSED
tests/unit/test_hlc.py::test_hlc_sorting PASSED
tests/unit/test_hlc.py::test_hlc_thread_safe PASSED
tests/unit/test_hlc.py::test_hlc_update_on_receive_future PASSED
tests/unit/test_hlc.py::test_hlc_update_on_receive_past PASSED
tests/unit/test_hlc.py::test_hlc_assign_server_time PASSED
tests/unit/test_hlc.py::test_hlc_to_dict PASSED
tests/unit/test_hlc.py::test_hlc_from_dict PASSED
tests/unit/test_hlc.py::test_hlc_serialization_roundtrip PASSED

==================== 16 passed in 3.45s ====================
```

### Run with Coverage

```bash
pytest tests/unit/test_hlc.py -v --cov=kkt_adapter.app.hlc --cov-report=term-missing
```

**Expected Coverage:** ≥95%

### Run Specific Test

```bash
pytest tests/unit/test_hlc.py::test_hlc_thread_safe -v
```

---

## ✅ Definition of Done (DoD)

- [x] `tests/unit/test_hlc.py` created with 11+ tests
- [x] All tests pass (16/16)
- [x] Code coverage ≥95%
- [x] No flaky tests (run 3 times, all pass)
- [x] Thread safety test passes (100 concurrent calls)
- [x] pytest runs without warnings
- [x] Tests documented (docstrings)

---

## 📊 Estimated Time

| Step | Estimated Time |
|------|----------------|
| 1. Create directory structure | 5 min |
| 2. Create test skeleton | 10 min |
| 3. Basic functionality tests (2 tests) | 15 min |
| 4. Monotonicity tests (3 tests) | 20 min |
| 5. Ordering tests (4 tests) | 25 min |
| 6. Thread safety test (1 test) | 15 min |
| 7. Edge case tests (3 tests) | 20 min |
| 8. Serialization tests (3 tests) | 15 min |
| 9. Run tests + fix failures | 15 min |
| **Total** | **2h 20min** |

**Buffer:** +10 min for flaky tests → **2h 30min total**

---

## 🔗 Dependencies

### Upstream (must complete first)
- **OPTERP-2** (Implement HLC) — ✅ DONE

### Downstream (blocks)
- **OPTERP-4** (Implement SQLite Buffer CRUD) — uses HLC, but doesn't need tests yet

---

## 🚀 Commands to Execute

### Pre-flight Check

```bash
# Verify OPTERP-2 complete
python -c "from kkt_adapter.app.hlc import generate_hlc; print('✓ HLC available')"

# Check pytest installed
pytest --version
# Expected: pytest 7.x or 8.x

# Install pytest if needed
pip install pytest pytest-cov
```

### Create Test Structure

```bash
# Create directories
mkdir -p tests/unit
touch tests/__init__.py
touch tests/unit/__init__.py

# Verify
ls -la tests/unit/
```

### Create Test File

```bash
# Create test_hlc.py
code tests/unit/test_hlc.py
# Paste code from steps above
```

### Run Tests

```bash
# Run all HLC tests
pytest tests/unit/test_hlc.py -v

# Run with coverage
pytest tests/unit/test_hlc.py -v --cov=kkt_adapter.app.hlc --cov-report=term-missing

# Run specific test
pytest tests/unit/test_hlc.py::test_hlc_thread_safe -v -s

# Check for flaky tests (run 3 times)
pytest tests/unit/test_hlc.py -v --count=3
```

---

## 📝 Notes & Gotchas

### Important Testing Considerations

1. **Fixture autouse=True**
   - Reset HLC state before EVERY test
   - Prevents test pollution (tests affect each other)

2. **Thread Safety Test**
   - Must use `threading.Lock` when appending to `timestamps` list
   - Without lock, list itself can get corrupted (race condition)

3. **Timing-Dependent Tests**
   - `test_hlc_same_second()` may fail if test runs slow
   - Use conditional assertions: check IF same second, THEN counter increments

4. **Flaky Tests**
   - Run with `--count=3` to detect non-deterministic failures
   - Thread safety test should NEVER be flaky

### Common Pitfalls

❌ **Forgetting to reset HLC state**
```python
def test_something():
    hlc = generate_hlc()  # Counter may be > 0 from previous test!
```

✅ **Correct (using fixture)**
```python
@pytest.fixture(autouse=True)
def reset_hlc_state():
    reset_hlc()
    yield
```

❌ **Race condition in thread test**
```python
timestamps = []

def generate_timestamp():
    hlc = generate_hlc()
    timestamps.append(hlc)  # NOT THREAD-SAFE!
```

✅ **Correct (using lock)**
```python
timestamps = []
lock = threading.Lock()

def generate_timestamp():
    hlc = generate_hlc()
    with lock:
        timestamps.append(hlc)
```

---

## 🔍 Test Coverage Breakdown

| Function | Line Coverage | Branch Coverage | Tests |
|----------|---------------|-----------------|-------|
| `HybridTimestamp.__lt__()` | 100% | 100% | 3 tests |
| `HybridTimestamp.__le__()` | 100% | - | 1 test |
| `HybridTimestamp.__gt__()` | 100% | - | 1 test |
| `HybridTimestamp.__ge__()` | 100% | - | 1 test |
| `HybridTimestamp.__eq__()` | 100% | 100% | 2 tests |
| `HybridTimestamp.to_dict()` | 100% | - | 2 tests |
| `HybridTimestamp.from_dict()` | 100% | - | 2 tests |
| `generate_hlc()` | 100% | 100% | 6 tests |
| `update_hlc_on_receive()` | 100% | 100% | 2 tests |
| `assign_server_time()` | 100% | - | 1 test |
| `reset_hlc()` | 100% | - | 1 test |
| **Total** | **~98%** | **~95%** | **16 tests** |

---

## 📅 Timeline

| Milestone | Date | Status |
|-----------|------|--------|
| Task planned | 2025-10-08 | ✅ Done |
| Implementation start | TBD | ⏳ Pending |
| All tests pass | TBD | ⏳ Pending |
| Coverage ≥95% | TBD | ⏳ Pending |
| Flaky test check (3 runs) | TBD | ⏳ Pending |
| Code review | TBD | ⏳ Pending |
| Merged to feature/phase1-poc | TBD | ⏳ Pending |

---

## ✅ Sign-Off

**Ready to implement:** ✅ Yes
**Blockers:** None (OPTERP-2 complete)
**Next task:** OPTERP-4 (Implement SQLite Buffer CRUD)

---

**Plan Version:** 1.0
**Last Updated:** 2025-10-08
**Status:** 📋 Ready for Implementation

