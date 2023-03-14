#-----------------------------------------------------------
# Global Parameters 
#-----------------------------------------------------------
THING_NAME := esp32
TOPIC := ESP32/Sensors
PWD := $(strip $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))) 

esptool:
	@echo "(1) Flashing precompiled firmware to ESP32 enabling Micropython."
	@echo ""
	esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash 
	esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 "$(strip $(PWD))/firmware/esp32-20220618-v1.19.1.bin"

DEVICE_ID := $(shell ampy --port /dev/ttyUSB0 run get_device_id.py)

aws : aws-device aws-policy aws-attach aws-clean 

aws-device:
	@echo "(2) Register device in AWS Iot Core."
	@echo "    Creating device certificates for AWS Iot Core."
	@aws iot create-keys-and-certificate \
        --set-as-active \
        --certificate-pem-outfile "$(strip $(PWD))/esp32/cert/certificate.pem.crt" \
        --public-key-outfile "$(strip $(PWD))/esp32/cert/public.pem.key" \
        --private-key-outfile "$(strip $(PWD))/esp32/cert/private.pem.key" \
		> logfile.json 
	
	@echo ""
	@echo "    Create thing representation for device."
	@aws iot create-thing --thing-name "$(strip $(THING_NAME))_$(strip $(DEVICE_ID))"

aws-policy:	
	@echo ""
	@echo "    Create policy to for thing."
	@aws iot create-policy \
		--policy-name "$(strip $(THING_NAME))_$(strip $(DEVICE_ID))" \
    	--policy-document '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["iot:Connect"], "Resource": ["arn:aws:iot:eu-central-1:19311246089:client/$(strip $(THING_NAME))_$(strip $(DEVICE_ID))"]}, {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:eu-central-1:193112460689:topic/$(TOPIC)"}]}'

aws-attach:
	@echo ""
	@echo "    Attach certificate to thing."
	@aws iot attach-thing-principal --principal $(shell cat logfile.json | grep -Po '"certificateArn": *\K"[^"]*"' logfile.json) --thing-name "$(strip $(THING_NAME))_$(strip $(DEVICE_ID))"

	@echo "    Attach policy to thing."
	@aws iot attach-policy --target $(shell cat logfile.json | grep -Po '"certificateArn": *\K"[^"]*"' logfile.json) --policy-name "$(strip $(THING_NAME))_$(strip $(DEVICE_ID))"

aws-clean:
    # Delete cache 
	@rm "$(strip $(PWD))/esp32/cert/public.pem.key" 
	@rm "$(strip $(PWD))/logfile.json"

ampy:
	@echo "(3) Flashing custom software for device $(DEVICE_ID)."
	@echo ""
	for file in $(strip $(PWD))/esp32/*; do \
		ampy --port /dev/ttyUSB0 put $${file}; \
		done

help:
	@echo ''
	@echo '  esptool    Flash precompiled firmware that enables Micropython on'
	@echo '             the ESP32. This sets the device up for running custom software.'
	@echo ''
	@echo '  aws        Register the device in AWS IoT Core.'
	@echo '             This step enables the device communicate with the MQTT broker'
	@echo '             and stream data to the DB.'
	@echo ''
	@echo '  ampy       Flashes custom software onto device using ampy.'
	@echo ''
