import pytest
from utils import calculate_mpg, celsius_to_fahrenheit

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

# ✅ Celsius to Fahrenheit: known points
def test_c_to_f_freezing():
    assert celsius_to_fahrenheit(0) == 32

def test_c_to_f_boiling():
    assert celsius_to_fahrenheit(100) == 212

def test_c_to_f_negative_forty():
    assert celsius_to_fahrenheit(-40) == -40

def test_c_to_f_decimal():
    assert celsius_to_fahrenheit(37.5) == 99.5

# ❌ Below absolute zero
def test_c_to_f_below_absolute_zero():
    with pytest.raises(ValueError):
        celsius_to_fahrenheit(-300)

# ❌ Wrong type
def test_c_to_f_invalid_type():
    with pytest.raises(TypeError):
        celsius_to_fahrenheit("25")
