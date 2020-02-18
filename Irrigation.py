import json
import requests
import logging
import os
import configparser

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
    config.read(dir + '\config')
    if(config.has_section('Default')):
        return {param:val for (param, val) in config.items('Default')}
    else:
        logger.error('Configuration file is missing Default section')
        return None

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

def activate_irrigation():
    #todo: Output to pi headers to activate valve for some period of time
    logger.info("Irrigation activated")

def main():
    config = get_config()

    if config is not None:
        weather = get_weather(config)

    if weather is not None:
        popToday = int(weather['LongTermPeriod'][0]['POPPercentDay'])
        popTomorrow = int(weather['LongTermPeriod'][1]['POPPercentDay'])
        if (popToday + popTomorrow >= 150):
            logger.info("Irrigation not activated due to PoP of " + str(popToday + popTomorrow) + " in the next 2 days")
        else:
            logger.info('Activating irrigation due to PoP of ' + str((popToday + popTomorrow)/2) + ' in the next 2 days')
            activate_irrigation()

    else:
        print('Failed request')
        # todo: Notify user

if __name__ == "__main__":
    main()