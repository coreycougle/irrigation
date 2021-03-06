import os
import ssl
import sys
import json
import time
import smtplib
import logging
import requests
import configparser
import RPi.GPIO as IO
from email.message import EmailMessage

logger = logging.getLogger()

# Configures logger to be used throughout script
def configure_logger():
    dir = os.path.abspath(os.path.dirname(__file__))
    log_path = dir + os.sep + 'irrigation.log'
    file_handler = logging.FileHandler(log_path)
    log_formatter = logging.Formatter('%(asctime)s-%(levelname)s-%(message)s')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

configure_logger()

# Grabs config file and returns weather, io, and email configurations as separate objects or as None
def get_config():
    config = configparser.ConfigParser()
    dir = os.path.abspath(os.path.dirname(__file__))
    config_path = dir + os.sep + 'config'
    config.read(config_path)
    if(config.has_section('Weather_API') and config.has_section('IO_Config') and config.has_section('Email_Config')):
        return {param:val for (param, val) in config.items('Weather_API')}, \
               {param:val for (param, val) in config.items('IO_Config')}, \
               {param:val for (param, val) in config.items('Email_Config')}
    else:
        logger.error('Configuration file is missing a section')
        return None, None, None

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

# Takes the Email Config and notifies user with message
def notify(config):
    message = EmailMessage()
    message.set_content("Please see logs for more detail")
    message['Subject'] = "Irrigation System Did Not Run"
    message['From'] = config['sender']
    message['To'] = config['receiver']
    context = ssl.create_default_context()

    with smtplib.SMTP(config['smtp_server'], int(config['port'])) as smtp:
        smtp.starttls(context=context)
        smtp.login(config['sender'], config['app_password'])
        smtp.send_message(message)
    logger.info("User Notified")


# Takes the io configuration and activates the irrigation valves sequentially
def activate_irrigation(config):
    try:
        IO.setwarnings(False)
        IO.setmode(IO.BCM)
        valve_list = [int(pin) for pin in config['valves'].split(',')]
        led = int(config['led'])
        IO.setup(led, IO.OUT)
        for valve in valve_list:
            IO.setup(valve, IO.OUT)
            IO.output(valve, IO.HIGH)
            logger.info(f'Valve on pin {valve} activated')
            for i in range(int(config['duration_minutes']) * 30):
                IO.output(led, IO.HIGH)
                time.sleep(1)
                IO.output(led, IO.LOW)
                time.sleep(1)
            IO.output(valve, IO.LOW)
            logger.info(f'Valve on pin {valve} deactivated')
    except Exception:
        IO.cleanup()
        logger.exception('GPIO failure')

# Checks if weather and io_config contain usable data,
# then checks if it will rain today or tomorrow,
# only activating irrigation if the combined PoP is below 150
def main():
    weather_config, io_config, email_config = get_config()

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

    else:
        if email_config is not None:
            notify(email_config)
        else:
            logger.error("Email Config is missing")

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
        valve_list = [int(pin) for pin in config[1]['valves'].split(',')]
        for valve in valve_list:
            IO.setup(valve, IO.OUT)
            IO.output(valve, IO.HIGH)
            time.sleep(5)
            IO.output(valve, IO.LOW)
            logger.info(f'Test Valve on pin {valve} Successful')
    except Exception:
        IO.cleanup()
        logger.exception('Test Valve Failed: GPIO failure')

# Calls the notify method when irrigation.py is run with -testnotify
def test_notify():
    config = get_config()
    notify(config[2])

if __name__ == "__main__":
    if len(sys.argv) == 1:
        main()
    elif len(sys.argv) == 2 and (sys.argv[1] == '-f' or sys.argv[1] == '-force'):
        force()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testsignal':
        test_signal()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testvalve':
        test_valve()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testnotify':
        test_notify()