#!/usr/bin/env python

from ConfigParser import SafeConfigParser
from boto3 import client
from datetime import datetime
import RPi.GPIO as gpio
import sys
import time

try:
    config_file = sys.argv[1]
    config = SafeConfigParser()
    config.read(config_file)
except IndexError:
    sys.exit('\nError: Please specify the config (.ini) file.\n')

PIN = config.getint('main', 'sensor_pin')
BEGIN_DELAY = config.getint('main', 'begin_delay')
END_DELAY = config.getint('main', 'end_delay')
START_MESSAGE = config.get('main', 'start_message')
END_MESSAGE = config.get('main', 'end_message')
BOOT_MESSAGE = config.get('main', 'boot_message')
PHONE = config.get('aws', 'phone')
ACCESS_KEY = config.get('aws', 'access_key')
SECRET_KEY = config.get('aws', 'secret_key')
REGION = config.get('aws', 'region')

sms = client(
    'sns',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name=REGION,
)

class sw40(object):
    def __init__(self, pin):
        self.pin = pin
        self.dryer_running = False
        self.last_vibration = time.time()
        self.vibration_start = time.time()
        self.vibrating = False
        gpio.setmode(gpio.BCM)
        gpio.setup(self.pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.add_event_detect(self.pin, gpio.RISING, callback=self.vibrated, bouncetime=1)

    def vibrated(self, pin):
        self.last_vibration = time.time()
        if not self.vibrating:
            self.vibration_start = self.last_vibration
            self.vibrating = True

    def heartbeat(self):
        current_time = time.time()
        dt_current_time = datetime.fromtimestamp(time.time())
        formatted_time = dt_current_time.strftime('%I:%M:%S %p')
        vibration_delta = self.last_vibration - self.vibration_start
        if self.vibrating and vibration_delta > BEGIN_DELAY and not self.dryer_running:
            self.send_active_message(formatted_time)
        elif not self.vibrating and self.dryer_running and current_time - self.last_vibration > END_DELAY:
            diff = dt_current_time - datetime.fromtimestamp(self.vibration_start)
            diffvals = str(diff).split(':')
            duration = '{}h{}m{}s'.format(diffvals[0], diffvals[1], int(float(diffvals[2])))
            self.send_inactive_message(formatted_time, duration)
        self.vibrating = current_time - self.last_vibration < 2
        if self.vibrating:
            print('vibrating for {}'.format(vibration_delta))

    def send_active_message(self, start):
        print('dryer has started')
        self.dryer_running = True
        sms.publish(PhoneNumber=PHONE, Message='{} at {}'.format(START_MESSAGE, start))

    def send_inactive_message(self, end, duration):
        print('dryer has finished')
        self.dryer_running = False
        sms.publish(PhoneNumber=PHONE, Message='{} End Time: {} Duration: {}'.format(END_MESSAGE, end, duration))


def main():
    sensor = sw40(PIN)
    print('Beginning to watch for good vibrations')
    try:
        while True:
            time.sleep(1)
            sensor.heartbeat()
    except KeyboardInterrupt:
        gpio.cleanup()


if __name__ == '__main__':
    main()
