import json
import requests
import logging
import os
import configparser
import RPi.GPIO as IO
import time

logger = logging.getLogger()
file_handler = logging.FileHandler('Irrigation.log')
log_formatter = logging.Formatter('%(asctime)s-%(levelname)s-%(message)s')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

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

def activate_irrigation(config):
    try:
        IO.setwarnings(False)
        IO.setmode(IO.BCM)
        valve1 = int(config['valve1'])
        valve2 = int(config['valve2'])
        led = int(config['led'])
        IO.setup((valve1, valve2, led), IO.OUT)
        IO.output((valve1, valve2, led), IO.HIGH)
        logger.info("Irrigation activated")
        time.sleep(int(config['duration_minutes']) * 60)
        IO.output((valve1, valve2, led), IO.LOW)
        logger.info("Irrigation deactivated")
    except Exception:
        IO.output((valve1, valve2, led), IO.LOW)
        logger.exception('GPIO failure')

def main():
    weather_config, io_config = get_config()

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

if __name__ == "__main__":
    main()