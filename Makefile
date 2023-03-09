#-----------------------------------------------------------
# Global Parameters 
#-----------------------------------------------------------
THING_NAME := esp32
POLICY := ESP32
PWD := $(strip $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))) 

esptool:
	@echo "(1) Flashing precompiled firmware to ESP32 enabling Micropython."
	@echo ""
	esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash 
	esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 "$(strip $(PWD))/firmware/esp32-20220618-v1.19.1.bin"

DEVICE_ID := $(shell ampy --port /dev/ttyUSB0 run get_device_id.py)

aws:
	@echo "(2) Register device in AWS Iot Core."
	@echo "    Creating device certificates for AWS Iot Core."
	@echo ""
	aws iot create-keys-and-certificate \
        --set-as-active \
        --certificate-pem-outfile "$(strip $(PWD))/esp32/cert/certificate.pem.crt" \
        --public-key-outfile "$(strip $(PWD))/esp32/cert/public.pem.key" \
        --private-key-outfile "$(strip $(PWD))/esp32/cert/private.pem.key" \
		> logfile.json 

	$(eval CERT_ARN := $(shell cat logfile.json | grep -Po '"certificateArn": *\K"[^"]*"' logfile.json))

	@echo ""
	@echo "Create thing representation for device."
	aws iot create-thing --thing-name "$(strip $(THING_NAME))_$(strip $(DEVICE_ID))"
	@echo ""
	@echo "Attach policy to certificate."
	aws iot attach-policy --target $(CERT_ARN) --policy-name "$(POLICY)"
	@echo ""
	@echo "Attach certificate to thing."
	aws iot attach-thing-principal --principal $(CERT_ARN) --thing-name "$(strip $(THING_NAME))_$(strip $(DEVICE_ID))"

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
