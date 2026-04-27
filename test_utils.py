import pytest
from utils import calculate_mpg

# ✅ Normal case
def test_mpg_normal():
    assert calculate_mpg(300, 10) == 30

# ❌ Fuel = 0
def test_zero_fuel():
    with pytest.raises(ValueError):
        calculate_mpg(100, 0)

# ❌ Negative values
def test_negative_values():
    with pytest.raises(ValueError):
        calculate_mpg(-100, 10)

# ❌ Wrong type
def test_invalid_type():
    with pytest.raises(TypeError):
        calculate_mpg("300", 10)

# failing test
def test_fail_demo():
    assert calculate_mpg(100, 10) == 50  # intentionally incorrect