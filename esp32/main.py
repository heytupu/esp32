"""Application Script"""
import json
import machine
import dht
import network
import ntptime
import time
from umqtt.simple import MQTTClient
import onewire, ds18x20

from scd30 import SCD30
from boot import CFG, logger

# Global settings from config file.
SSID = CFG["Network"]["SSID"]
PASS = CFG["Network"]["PASS"]

DEVICE_ID = int.from_bytes(machine.unique_id(), "little")
THING_NAME = f"{CFG["AWS_IOT_core"]["THING_NAME"]}_{str(DEVICE_ID)}"
TOPIC = CFG["AWS_IOT_core"]["TOPIC"]
ENDPOINT = CFG["AWS_IOT_core"]["ENDPOINT"]

ROOT_CA = open(CFG["AWS_IOT_core"]["ROOT_CA"], "r").read()
CERTIFICATE = open(CFG["AWS_IOT_core"]["CERTIFICATE"], "r").read()
PRIVATE_KEY = open(CFG["AWS_IOT_core"]["PRIVATE_KEY"], "r").read()
SSL_CONFIG = {"key": PRIVATE_KEY, "cert": CERTIFICATE, "server_side": False}

TIME_INTERVAL = CFG["Device_settings"]["Time_Interval"]
DEVICE_LOCATION = CFG["Device_settings"]["location"]
UTC_OFFSET = CFG["Device_settings"]["UTC_Offset"]

# Sensor Bool for setting wether specific sensor is used or not.
SCD30_BOOLEAN = CFG["Sensors"]["SCD30"]["Boolean"]
MOISTURE_BOOLEAN = CFG["Sensors"]["Moisture_Sensor"]["Boolean"]
DS18B20_BOOLEAN = CFG["Sensors"]["DS18B20"]["Boolean"]
AM2302_BOOLEAN = CFG["Sensors"]["AM2302"]["Boolean"]

# Sets which pins the sensors use. Each sensor uses a different number of pins.
SCD30_PIN = CFG["Sensors"]["SCD30"]["Pin"]
# MOISTURE_PIN = CFG["Sensors"]["Moisture_Sensor"]["Pin"]
DS18B20_PIN = CFG["Sensors"]["DS18B20"]["Pin"]
AM2302_PIN = CFG["Sensors"]["AM2302"]["Pin"]
# This is used to give names to each sensor when we publish the data.
DS18B20_NAME = CFG["Sensors"]["DS18B20"]["Name"]


def get_datetime():
    """Returns a readable date and time. 
    This way, one does not need to solely rely upon the timestamp."""
    # Need to update this so it pulls the time from the internet connection.
    offset = UTC_OFFSET * 60**2
    year, month, day, hour, mins, secs, _, _ = time.localtime(time.time() + offset)

    datetime = "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        year, month, day, hour, mins, secs
    )

    return datetime


def message_callback(topic: str, message: str) -> None:
    """Callback for MQTT client."""
    print(json.loads(message))


def connect_iot_core() -> MQTTClient:
    """Establish a connection AWS Iot Core MQTT broker."""
    mqtt = MQTTClient(
        THING_NAME,
        ENDPOINT,
        port=8883,
        keepalive=10000,
        ssl=True,
        ssl_params=SSL_CONFIG,
    )
    print(f"MQTT Client {mqtt.client_id} connects to {mqtt.server}.")
    if __debug__:
        logger.debug(f"MQTT Client {mqtt.client_id} connects to {mqtt.server}.")
    try:
        mqtt.connect()
        mqtt.set_callback(message_callback)
        print(f"Established connection to MQTT broker at {ENDPOINT}.")
    except Exception as e:
        raise Exception(f"Unable to connect to MQTT broker. {e}")

    return mqtt


def AM2302_sensor_data():
    """Connect to AM2302 sensor and return temperature and humidity."""
    d = dht.DHT22(machine.Pin(AM2302_PIN))
    data = {}

    retry = 0
    while retry < 3:
        try:
            d.measure()
            break
        except:
            retry = retry + 1
            
    data = {"temperature": d.temperature(), "humidity": d.humidity()}

    return data


def data_from_SCD30():
    """Connect to SCD30 and return temperature, humidity, and co2."""
    # Set up i2c protocol for the SCD30
    i2c = machine.SoftI2C(scl=machine.Pin(22), sda=machine.Pin(21), freq=10000)

    try:
        # If SCD30 has not been connected attempt to connect to it.
        scd30 = SCD30(i2c, 0x61)
    except:
        print("Failed to connect to SCD30. Please make sure the sensor is connected.")

    missingSCD30 = False
    # Try to take measurement from scd30
    try:
        # Wait until sensor has a measurement ready to be read
        while scd30.get_status_ready() != 1:
            time.sleep_ms(200)

        # Take measurement from SCD30
        (co2, temperature, humidity) = scd30.read_measurement()
    except:
        # If sensor is not connected use zeroes.
        missingSCD30 = True
        (co2, temperature, humidity) = (0, 0, 0)

    # Add in offsets from config file
    co2 = co2 + CFG["SCD30_offsets"]["co2Offset"]
    temperature = temperature + CFG["SCD30_offsets"]["tempOffset"]
    humidity = humidity + CFG["SCD30_offsets"]["humidityOffset"]

    print(
        "\nValues captured:",
        "CO2:",
        co2,
        "Temperature:",
        temperature,
        "Humidity:",
        humidity,
    )

    return {"temperature": temperature, "co2": co2, "humidity": humidity}


def moisture_sensor_data():
    """Gathers the data collected from any moisture sensors attached to the sensor."""
    moisture1 = machine.ADC(machine.Pin(32))
    moisture1.atten(machine.ADC.ATTN_11DB)

    moisture2 = machine.ADC(machine.Pin(33))
    moisture2.atten(machine.ADC.ATTN_11DB)

    moisture3 = machine.ADC(machine.Pin(34))
    moisture3.atten(machine.ADC.ATTN_11DB)

    moisture4 = machine.ADC(machine.Pin(35))
    moisture4.atten(machine.ADC.ATTN_11DB)

    # Take measurements from Moisture Sensor
    moistureValue1 = moisture1.read()
    moistureValue2 = moisture2.read()
    moistureValue3 = moisture3.read()
    moistureValue4 = moisture4.read()

    # Normalize moisture measurements to a percentage using the maximum 
    # sensor value, 4095.
    #
    # Immersing the sensor in water registers about 62% so it
    # makes sense to set that as the 100% moisture point
    moistureValue1 = 4095 - moistureValue1
    moistureValue1 = moistureValue1 * (100 / 4095) * (100 / 63)
    print("Moisture1:", moistureValue1)

    moistureValue2 = 4095 - moistureValue2
    moistureValue2 = moistureValue2 * (100 / 4095) * (100 / 63)
    print("Moisture2:", moistureValue2)

    moistureValue3 = 4095 - moistureValue3
    moistureValue3 = moistureValue3 * (100 / 4095) * (100 / 63)
    print("Moisture3:", moistureValue3)

    moistureValue4 = 4095 - moistureValue4
    moistureValue4 = moistureValue4 * (100 / 4095) * (100 / 63)
    print("Moisture4:", moistureValue4)

    data = {}

    # Add moisture measurements if they are not blank (Wired to 3.3Vcc).
    if moistureValue1 > 1:
        data["moisture_1"] = moistureValue1
    if moistureValue2 > 1:
        data["moisture_2"] = moistureValue2
    if moistureValue3 > 1:
        data["moisture_3"] = moistureValue3
    if moistureValue4 > 1:
        data["moisture_4"] = moistureValue4

    return data


def DS18B20_sensor_data():
    """This method was built to measure the temperatures of the water
    coming into the farm from the roof."""
    print(DS18B20_PIN)
    data = {}
    for pin in range(0, len(DS18B20_PIN)):
        try:
            ds_pin = machine.Pin(DS18B20_PIN[pin])
            ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

            roms = ds_sensor.scan()

            ds_sensor.convert_temp()
            time.sleep_ms(750)
            data[DS18B20_NAME[pin]] = ds_sensor.read_temp(roms[0])
        except:
            try:
                print(f"{DS18B20_NAME[pin]} failed to respond.")
            except:
                print("Unknown Pipe Sensor failed.")

    return data


def publish(mqtt_client: MQTTClient, topic: str, value: int) -> None:
    """Publish the data to the MQTT broker."""
    try:
        mqtt_client.publish(topic, value)
        print(f"Published value {value} to topic '{topic}'.")
    except Exception as error:
        print(f"Failed to publish sensor data for topic '{topic}'. {error}")


if __name__ == "__main__":
    mqtt_client = connect_iot_core()

    try:
        ntptime.settime()
    except:
        print("Setting current time failed.")

    starting_time = time.time()
    while True:
        data = {
            "datetime": get_datetime(),
            "device_id": DEVICE_ID,
            "location": DEVICE_LOCATION,
        }

        # Gather data from the sensor specified.
        if SCD30_BOOLEAN:
            scd30_data = data_from_SCD30()
            data.update(scd30_data)
        if MOISTURE_BOOLEAN:
            moisture_data = moisture_sensor_data()
            data.update(moisture_data)
        if DS18B20_BOOLEAN:
            DS18B20_data = DS18B20_sensor_data()
            data.update(DS18B20_data)
        if AM2302_BOOLEAN:
            AM2302_data = AM2302_sensor_data()
            data.update(AM2302_data)

        # Push the data to the MQTT broker in AWS Iot Core.
        publish(mqtt_client, "ESP32/Sensors", json.dumps(data))

        # Control the interval of publishing data.
        time.sleep(TIME_INTERVAL)

        # # if (time.time() - starting_time) > (7 * 24 * 60 * 60):
        if (time.time() - starting_time) > (5 * 60):
            print("Performing reset.")
            machine.reset()

# Firmware Notes:
"""
1. Do not use pin 12 for anything. There is an error thta can occur when using
this pin. It makes it impossible to start the program. You can't even cancel it
with Ctrl. "C". 
"""
