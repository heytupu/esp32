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
	@echo "    Create policy for thing."
	@aws iot create-policy \
		--policy-name "$(strip $(THING_NAME))_$(strip $(DEVICE_ID))" \
    	--policy-document '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["iot:Connect"], "Resource": ["arn:aws:iot:eu-central-1:193112460689:client/$(strip $(THING_NAME))_$(strip $(DEVICE_ID))"]}, {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:eu-central-1:193112460689:topic/$(TOPIC)"}]}'

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

ifeq (certs, $(filter certs,$(MAKECMDGOALS)))
	@echo 'Flashing device with the specified certificates as certs is set.'
	@for file in $(strip $(PWD))/esp32/*; do \
		echo "$${file}"; \
		ampy --port /dev/ttyUSB0 put $${file}; \
		done
else
	@echo 'Flashing device without certificates.'
	@for file in $(strip $(PWD))/esp32/*; do \
		echo "$${file}"; \
		if [ $${file} != $(strip $(PWD))/esp32/cert ]; then \
			ampy --port /dev/ttyUSB0 put $${file}; \
    	fi; \
	done
endif


help:
	@echo ''
	@echo '  esptool      Flash precompiled firmware that enables Micropython on'
	@echo '               the ESP32. This sets the device up for running custom software.'
	@echo ''
	@echo '  aws          Register the device in AWS IoT Core.'
	@echo '               This step enables the device communicate with the MQTT broker'
	@echo '               and stream data to the DB.'
	@echo ''
	@echo '               The aws consists of various sub commands'
	@echo '  aws-device   Registers the device at AWS IoT Core and creates certificates for it.' 
	@echo '  aws-policy   Creates a unique policy for the device.' 
	@echo '  aws-attach   Attaches the certificates to the policy and the policy to the thing.' 
	@echo '  aws-clean    Clean up afterwards.' 
	@echo ''
	@echo '  ampy         Flashes custom software onto device using ampy.'
	@echo ''
	@echo '               The default runs without overwriting the certificates.'
	@echo '  ampy certs   To overwrite the certificates as well, please add the flag certs to the command.'
	@echo ''
