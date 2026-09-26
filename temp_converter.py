from utils import celsius_to_fahrenheit

print("This program converts temperature from Celsius to Fahrenheit.")

celsius = float(input("Enter temperature (°C): "))

fahrenheit = celsius_to_fahrenheit(celsius)

print(f"{celsius:.2f} °C = {fahrenheit:.2f} °F")
