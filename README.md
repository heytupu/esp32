<h1 align="center">
  <b>ESP32</b><br>
</h1>

## Prepare ESP32 for Usage with AWS

Tupu works with the [ESP32](https://www.espressif.com/en/products/socs/esp32) microcontroller which handles the communication between the sensor and further peripherals. It essentially fetches data from the sensor and streams it to the cloud. The cloud provider is AWS.

AWS provides a service called AWS Iot Core which basically implements a MQTT broker along with device authentication. The MQTT broker sends the data afterwards to the DynamoDB (noSQL) database.

All the code that will run on the ESP32 is stored in `esp32/`. Each device receives unique certificates 
from AWS for authentication and a slightly adjusted `config.json` file where parameters for the individual 
device can be set.

For installing the whole software in one go, please make sure the **device is plugged** via `/dev/ttyUSB0` and run:
```bash
make esptool && make aws && make ampy
```

Please make sure all prerequisits are installed.

### Prerequisits

- **AWS CLI**

Make sure to have the [aws cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed on your system. 

```bash
# Linux x86 (64-bit)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install 
```

Please make sure that you have the credentials in place as well the `AWSIoTFullAccess` policy is attached to the your specific user. A guide on how to set the credentials can be found [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).

- **ESPTOOL**

The latest stable [esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32/installation.html) release can be installed from PyPI via pip:
```bash
pip install esptool 
```

- **AMPY**

MicroPython Tool [ampy](https://github.com/scientifichackers/ampy) - Utility to interact with a CircuitPython or MicroPython board over a serial connection.
```bash
pip install adafruit-ampy
```
