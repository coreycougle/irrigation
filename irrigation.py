import os
import sys
import json
import time
import logging
import requests
import configparser
import RPi.GPIO as IO

logger = logging.getLogger()
file_handler = logging.FileHandler('irrigation.log')
log_formatter = logging.Formatter('%(asctime)s-%(levelname)s-%(message)s')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

# Grabs config file and returns weather configuration and io configuration as separate objects or as None
def get_config():
    config = configparser.ConfigParser()
    dir = os.path.abspath(os.path.dirname(__file__))
    config_path = dir + os.sep + 'config'
    config.read(config_path)
    if(config.has_section('Weather_API') and config.has_section('IO_Config')):
        return {param:val for (param, val) in config.items('Weather_API')}, {param:val for (param, val) in config.items('IO_Config')}
    else:
        logger.error('Configuration file is missing a section')
        return None, None

#Takes the weather configuration and calls the weather API
# then returns a collection of forcasted weather data
def get_weather(config):
    headers = {'Accept': 'application/json',
               'x-api-key': config['api_key']}
    api_url = config['api_url_base'] + config['country'] + '/' + config['city']

    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))
    else:
        logger.error('Bad Response, %s', response)
        return None

# Takes the io configuration and activates the irrigation valves
def activate_irrigation(config):
    try:
        IO.setwarnings(False)
        IO.setmode(IO.BCM)
        valve1 = int(config['valve1'])
        valve2 = int(config['valve2'])
        led = int(config['led'])
        IO.setup((valve1, valve2, led), IO.OUT)
        IO.output((valve1, valve2), IO.HIGH)
        logger.info("Irrigation activated")
        for i in range(int(config['duration_minutes']) * 30):
            IO.output(led, IO.HIGH)
            time.sleep(1)
            IO.output(led, IO.LOW)
            time.sleep(1)
        IO.output((valve1, valve2, led), IO.LOW)
        logger.info("Irrigation deactivated")
    except Exception:
        IO.output((valve1, valve2, led), IO.LOW)
        logger.exception('GPIO failure')

# Checks if weather and io_config contain usable data,
# then checks if it will rain today or tomorrow,
# only activating irrigation if the combined PoP is below 150
def main():
    weather_config, io_config = get_config()
    weather = None
    if weather_config is not None:
        weather = get_weather(weather_config)
    else:
        logger.error('Weather config is missing')

    if weather is not None:
        popToday = int(weather['LongTermPeriod'][0]['POPPercentDay'])
        popTomorrow = int(weather['LongTermPeriod'][1]['POPPercentDay'])
        if popToday + popTomorrow >= 150:
            logger.info("Irrigation not activated due to PoP of " + str(popToday + popTomorrow) + " in the next 2 days")
        elif io_config is not None:
            logger.info('Activating irrigation due to PoP of ' + str((popToday + popTomorrow)/2) + ' in the next 2 days')
            activate_irrigation(io_config)
        else:
            # Once configured, the IO config won't change, so no need to include it with the user notification logic
            logger.error('IO config is missing')

    # else:
        # todo: Notify user regarding issues with weather API service

# Forces the activate_irrigation method when irrigation.py is run with -f or -force
def force():
    config = get_config()
    activate_irrigation(config[1])

# Flashes the test led when irrigation.py is run with -testsignal
def test_signal():
    config = get_config()
    try:
        IO.setwarnings(False)
        IO.setmode(IO.BCM)
        led = int(config[1]['led'])
        IO.setup(led, IO.OUT)
        for i in range(3):
            IO.output(led, IO.HIGH)
            time.sleep(1)
            IO.output(led, IO.LOW)
            time.sleep(1)
        logger.info("Test Signal Successful")
    except Exception:
        IO.output(led, IO.LOW)
        logger.exception('Test Signal Failed: GPIO failure')

# Activates the irrigation valves for 5 seconds when irrigation.py is run with -testvalve
def test_valve():
    config = get_config()
    try:
        IO.setwarnings(False)
        IO.setmode(IO.BCM)
        valve1 = int(config[1]['valve1'])
        valve2 = int(config[1]['valve2'])
        IO.setup((valve1,valve2), IO.OUT)
        IO.output((valve1,valve2), IO.HIGH)
        time.sleep(5)
        IO.output((valve1,valve2), IO.LOW)
        logger.info("Test Valve Successful")
    except Exception:
        IO.output((valve1,valve2), IO.LOW)
        logger.exception('Test Valve Failed: GPIO failure')

if __name__ == "__main__":
    if len(sys.argv) == 1:
        main()
    elif len(sys.argv) == 2 and (sys.argv[1] == '-f' or sys.argv[1] == '-force'):
        force()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testsignal':
        test_signal()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testvalve':
        test_valve()