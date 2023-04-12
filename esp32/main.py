"""Application Script"""
import json
import machine
import dht
import network
import time
from umqtt.simple import MQTTClient
import onewire, ds18x20
import gc

from ntptime import ntptime
from scd30 import SCD30
from boot import CFG, sta_if, connect_wifi, logger

# Global settings from config file.
#
# WIFI Settings.
SSID = CFG["Network"]["SSID"]
PASS = CFG["Network"]["PASS"]
# Device Settings
DEVICE_ID = int.from_bytes(machine.unique_id(), "little")
THING_NAME = f"{CFG["AWS_IOT_core"]["THING_NAME"]}_{str(DEVICE_ID)}"
# Publishing Topics
PUB_TOPIC = CFG["AWS_IOT_core"]["TOPIC"]
# Subscription Topics
# SUB_TOPICS = ["ESP32/all/update/ota", f"ESP32/{THING_NAME}/update/ota"]
SUB_TOPICS = [f"ESP32/{THING_NAME}/update/ota"]
# Unused: Will be removed in the future.
SUB_TOPIC = "ESP32/all/update/ota"
SUB_TOPIC_CONFIG = f"ESP32/{THING_NAME}/update/config"
SUB_TOPIC_OTA = f"ESP32/{THING_NAME}/update/ota"
SUB_TOPIC_CERTS = f"ESP32/{THING_NAME}/update/certs"
# AWS Server Endpoint.
ENDPOINT = CFG["AWS_IOT_core"]["ENDPOINT"]
# AWS Certificates.
ROOT_CA = open(CFG["AWS_IOT_core"]["ROOT_CA"], "r").read()
CERTIFICATE = open(CFG["AWS_IOT_core"]["CERTIFICATE"], "r").read()
PRIVATE_KEY = open(CFG["AWS_IOT_core"]["PRIVATE_KEY"], "r").read()
SSL_CONFIG = {"key": PRIVATE_KEY, "cert": CERTIFICATE, "server_side": False}

# General Settings
TIME_INTERVAL = CFG["Device_settings"]["Time_Interval"]
DEVICE_LOCATION = CFG["Device_settings"]["location"]
UTC_OFFSET = CFG["Device_settings"]["UTC_Offset"]

# Sensor flags for whether a specific sensor is used.
SCD30_BOOLEAN = CFG["Sensors"]["SCD30"]["Boolean"]
MOISTURE_BOOLEAN = CFG["Sensors"]["Moisture_Sensor"]["Boolean"]
DS18B20_BOOLEAN = CFG["Sensors"]["DS18B20"]["Boolean"]
AM2302_BOOLEAN = CFG["Sensors"]["AM2302"]["Boolean"]

# Sets which pins are used by the sensors. Each sensor uses a different number of pins.
SCD30_PIN = CFG["Sensors"]["SCD30"]["Pin"]
# MOISTURE_PIN = CFG["Sensors"]["Moisture_Sensor"]["Pin"]
DS18B20_PIN = CFG["Sensors"]["DS18B20"]["Pin"]
AM2302_PIN = CFG["Sensors"]["AM2302"]["Pin"]

# Defines the Sensor names.
DS18B20_NAME = CFG["Sensors"]["DS18B20"]["Name"]
#
# Process Parameters
RETRY = 10
# 
PUB_RETRY = 5


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


def message_callback(b_topic: str, b_msg: str) -> None:
    """Callback for MQTT client."""
    # Decoding the subscription message.
    msg = json.loads(b_msg)
    topic = b_topic.decode("utf-8")

    logger.info(f"Received {msg} from mqtt broker via topic {topic}.")

    if topic == SUB_TOPICS[0] or topic == SUB_TOPICS[1]:
        if "update" in msg:
            if msg["update"]:
                logger.info("\nPerforming a machine reset.\n")
                # Perform a machine reset in order to trigger the ugit logic.
                machine.reset()


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
    if __debug__:
        logger.debug(f"MQTT Client {mqtt.client_id} connects to {mqtt.server}.")

    mqtt.set_callback(message_callback)
    r = 0
    while True: 
        try:
            mqtt.connect()
            logger.info(f"Established connection to MQTT broker at {ENDPOINT}.")
            break
        except Exception as e:
            logger.error(f"Unable to connect to MQTT broker. {e}")
            r = r + 1
            if r == RETRY:
                machine.reset()

    # Subscribe to defined topics in order to be able to access the device.
    subscribe(mqtt)

    return mqtt


def data_from_AM2302():
    """Connect to AM2302 sensor and return temperature and humidity."""
    if __debug__:
        logger.debug(f"AM2302 Pin : {AM2302_PIN}")

    d = dht.DHT22(machine.Pin(AM2302_PIN))

    r = 0
    while r < RETRY:
        try:
            d.measure()
            break
        except:
            r = r + 1

    logger.info(f"AM2302: Temperature: {d.temperature()} | Humidity: {d.humidity()}")
    return {"temperature": d.temperature(), "humidity": d.humidity()}


def data_from_SCD30():
    """Connect to SCD30 and return temperature, humidity, and co2."""
    # Set up i2c protocol for the SCD30
    i2c = machine.SoftI2C(scl=machine.Pin(22), sda=machine.Pin(21), freq=10000)
    try:
        # If SCD30 has not been connected attempt to connect to it.
        scd30 = SCD30(i2c, 0x61)
    except:
        logger.warning(
            "Failed to connect to SCD30. Please make sure the sensor is connected."
        )

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
        (co2, temperature, humidity) = (0.0, 0.0, 0.0)

    # Add in offsets from config file
    co2 = co2 + CFG["SCD30_offsets"]["co2Offset"]
    temperature = temperature + CFG["SCD30_offsets"]["tempOffset"]
    humidity = humidity + CFG["SCD30_offsets"]["humidityOffset"]

    logger.info(
        f"SCD30: CO2: {co2} | Temperature: {temperature} | Humidity: {humidity}"
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

    moistureValue2 = 4095 - moistureValue2
    moistureValue2 = moistureValue2 * (100 / 4095) * (100 / 63)

    moistureValue3 = 4095 - moistureValue3
    moistureValue3 = moistureValue3 * (100 / 4095) * (100 / 63)

    moistureValue4 = 4095 - moistureValue4
    moistureValue4 = moistureValue4 * (100 / 4095) * (100 / 63)

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

    logger.info(
        f"\nValues captured: \
                Moisture 1: {moistureValue1} | \
                Moisture 2: {moistureValue2} | \
                Moisture 3: {moistureValue3} | \
                Moisture 4: {moistureValue4}"
    )
    return data


def data_from_DS18B20():
    """This method was built to measure the temperatures of the water
    coming into the farm from the roof."""
    if __debug__:
        logger.debug(f"DS18B20 Pin : {DS18B20_PIN}")

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
                logger.error(f"{DS18B20_NAME[pin]} failed to respond.")
            except:
                logger.error("Unknown Pipe Sensor failed.")
    return data


def subscribe(mqtt_client: MQTTClient) -> None:
    """Subscribe to all topics from MQTT broker."""
    for topic in SUB_TOPICS:
        try:
            mqtt_client.subscribe(topic)
            logger.info(f"Subscribed to topic {topic}")
        except Exception as e:
            logger.warning(f"Failed to subscribe to {topic}. {e}")


def publish(mqtt_client: MQTTClient, topic: str, value: int) -> None:
    """Publish the data to the MQTT broker."""
    try:
        mqtt_client.publish(topic, value)
        logger.info(f"Published value {value} to topic '{topic}'")
    except Exception as error:
        logger.warning(f"Failed to publish sensor data for topic '{topic}'. {error}")


if __name__ == "__main__":
    mqtt_client = connect_iot_core()
    gc.enable()
    
    r = 0
    while True:
        # Sets the correct time otherwise the default of UNIX starting time is used as reference.
        try:
            ntptime.settime()
            break
        except:
            logger.warning("Setting current time failed.")
            r = r + 1
            if r == RETRY:
                machine.reset()
            time.sleep(1)

    # Set a time counter.
    starting_time = time.time()
    # Message counter
    msg_c = 0
    while True:
        # Make sure WIFI still connected.
        if sta_if.isconnected():
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
                ds18B20_data = data_from_DS18B20()
                data.update(ds18B20_data)
            if AM2302_BOOLEAN:
                am2302_data = data_from_AM2302()
                data.update(am2302_data)

            try:
                # Check for newly arrived messages via subscription topics
                mqtt_client.check_msg()
            except:
                logger.warning("Receiving message from broker failed.")
            
            # As umqtt does not offer a simply still connected function this is they 
            # way around it.
            try:
                # Push the data to the MQTT broker in AWS Iot Core.
                publish(mqtt_client, PUB_TOPIC, json.dumps(data))
                msg_c = 0
            except:
                logger.warning(f"Failed to publish to {PUB_TOPIC}. Retry {msg_c}.")
                if msg_c == PUB_RETRY:
                    machine.reset()
                msg_c = msg_c + 1

            # Control the interval of publishing data.
            time.sleep(TIME_INTERVAL)
            gc.collect()
        else:
            sta_if = connect_wifi()
