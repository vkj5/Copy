def calculate_mpg(distance: float, fuel: float) -> float:
    if not isinstance(distance, (int, float)) or not isinstance(fuel, (int, float)):
        raise TypeError("Inputs must be numbers.")

    if fuel == 0:
        raise ValueError("Fuel cannot be zero.")

    if distance < 0 or fuel < 0:
        raise ValueError("Distance and fuel must be non-negative.")

    return round(distance / fuel, 2)



def celsius_to_fahrenheit(celsius: float) -> float:
    if isinstance(celsius, bool) or not isinstance(celsius, (int, float)):
        raise TypeError("Temperature must be a number.")

    if celsius < -273.15:
        raise ValueError("Temperature cannot be below absolute zero (-273.15 °C).")

    return round(celsius * 9 / 5 + 32, 2)
