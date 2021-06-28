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

# Takes the weather configuration and calls the weather API
# then returns a collection of forcasted weather data
def get_weather(config):
    headers = {'Accept': 'application/json', 'Accept-Encoding': 'gzip'}
    country = config['country']
    api_key = config['api_key']
    city = config['city']
    country_code = config['country_code']

    location_api = config['location_api'].format(country=country, api_key=api_key, city=city, country_code=country_code)
    locate_url = config['api_url_base'] + location_api

    location_response = requests.get(locate_url, headers=headers)

    if location_response.status_code != 200:
        logger.error('Bad Location Response, %s', location_response)
        return None

    location_data = json.loads(location_response.content.decode('utf-8'))
    location_key = location_data[0]['Key']

    forecast_api = config['forecast_api'].format(location_key=location_key, api_key=api_key, country_code=country_code)
    forecast_url = config['api_url_base'] + forecast_api

    forecast_response = requests.get(forecast_url, headers=headers)

    if forecast_response.status_code != 200:
        logger.error('Bad Forecast Response, %s', location_response)
        return None

    forecast_data = json.loads(forecast_response.content.decode('utf-8'))

    return forecast_data

def willItRain(weather):
    popToday = int(weather['DailyForecasts'][0]['Day']['RainProbability'])
    popTonight = int(weather['DailyForecasts'][0]['Night']['RainProbability'])
    amountToday = float(weather['DailyForecasts'][0]['Day']['Rain']['Value'])
    amountTonight = float(weather['DailyForecasts'][0]['Night']['Rain']['Value'])

    popTomorrowDay = int(weather['DailyForecasts'][1]['Day']['RainProbability'])
    popTomorrowNight = int(weather['DailyForecasts'][1]['Night']['RainProbability'])
    amountTomorrowDay = float(weather['DailyForecasts'][1]['Day']['Rain']['Value'])
    amountTomorrowNight = float(weather['DailyForecasts'][1]['Night']['Rain']['Value'])

    itWillRain = {
        'today': True if popToday > 50 and amountToday > 1 else False,
        'tonight': True if popTonight > 50 and amountTonight > 1 else False,
        'tomorrowDay': True if popTomorrowDay > 50 and amountTomorrowDay > 1 else False,
        'tomorrowNight': True if popTomorrowNight > 50 and amountTomorrowNight > 1 else False
    }
    return True in itWillRain.values()

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
def activate_irrigation(config, predictedRain):
    # If rain is predicted, we extend the duration of irrigation to free up more storage capacity
    multiplier = 3 if predictedRain else 1

    try:
        IO.setwarnings(False)
        IO.setmode(IO.BCM)
        valve_list = [int(pin) for pin in config['valves'].split(',')]
        duration_list = [int(duration) for duration in config['durations'].split(',')]
        led = int(config['led'])
        IO.setup(led, IO.OUT)
        for index in range(len(valve_list)):
            IO.setup(valve_list[index], IO.OUT)
            IO.output(valve_list[index], IO.HIGH)
            logger.info(f'Valve on pin {valve_list[index]} activated')
            # We loop 30 times because each cycle of the notification led is 2 seconds
            for i in range(duration_list[index] * 30 * multiplier):
                IO.output(led, IO.HIGH)
                time.sleep(1)
                IO.output(led, IO.LOW)
                time.sleep(1)
            IO.output(valve_list[index], IO.LOW)
            logger.info(f'Valve on pin {valve_list[index]} deactivated')
    except Exception:
        IO.cleanup()
        logger.exception('GPIO failure in activate_irrigation')

# Checks if weather and io_config contain usable data,
# then checks if it will rain today or tomorrow,
# activating irrigation if it will not rain in the next two days,
# or dumping the water reserve to capture more predicted rain
def main():
    weather_config, io_config, email_config = get_config()

    if weather_config is None or io_config is None or email_config is None:
        print('Irrigation failed: Config is missing. Check log file')
        return

    weather = get_weather(weather_config)
    predictedRain = willItRain(weather)
    activate_irrigation(io_config, predictedRain)

# Forces the activate_irrigation method when irrigation.py is run with -f or -force
def force():
    config = get_config()
    logger.info("Forcing irrigation")
    activate_irrigation(config[1])

# Flashes the test led when irrigation.py is run with -testcircuit
def test_circuit():
    config = get_config()
    logger.info("Testing the circuit")
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
        logger.info("Test Circuit Successful")
    except Exception:
        IO.output(led, IO.LOW)
        logger.exception('Test Circuit Failed: GPIO failure')

# Activates the irrigation valves for 5 seconds when irrigation.py is run with -testvalve
def test_valve():
    config = get_config()[1]
    logger.info("Testing the valve electronics and plumbing")
    try:
        IO.setwarnings(False)
        IO.setmode(IO.BCM)
        valve_list = [int(pin) for pin in config['valves'].split(',')]
        for valve in valve_list:
            IO.setup(valve, IO.OUT)
            IO.output(valve, IO.HIGH)
            time.sleep(5)
            IO.output(valve, IO.LOW)
            logger.info(f'Test Valve on pin {valve} Successful')
    except Exception:
        IO.cleanup()
        logger.exception('Test Valve Failed: GPIO failure')

# Tests whether or not weather service is connected correctly by printing the parsed weather data
def test_weather():
    config = get_config()[0]
    logger.info("Testing the Weather API connection")
    weather = get_weather(config)

    popToday = int(weather['DailyForecasts'][0]['Day']['RainProbability'])
    popTonight = int(weather['DailyForecasts'][0]['Night']['RainProbability'])
    amountToday = float(weather['DailyForecasts'][0]['Day']['Rain']['Value'])
    amountTonight = float(weather['DailyForecasts'][0]['Night']['Rain']['Value'])

    popTomorrowDay = int(weather['DailyForecasts'][1]['Day']['RainProbability'])
    popTomorrowNight = int(weather['DailyForecasts'][1]['Night']['RainProbability'])
    amountTomorrowDay = float(weather['DailyForecasts'][1]['Day']['Rain']['Value'])
    amountTomorrowNight = float(weather['DailyForecasts'][1]['Night']['Rain']['Value'])

    print(f"Today's PoP is {popToday}% with an amount of {amountToday}mm")
    print(f"Tonight's PoP is {popTonight}% with an amount of {amountTonight}mm")
    print(f"Tomorrow's PoP is {popTomorrowDay}% with an amount of {amountTomorrowDay}mm")
    print(f"Tomorrow night's PoP is {popTomorrowNight}% with an amount of {amountTomorrowNight}mm")

# Calls the notify method when irrigation.py is run with -testnotify
def test_notify():
    config = get_config()[2]
    logger.info("Testing the notification connection")
    notify(config)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        main()
    elif len(sys.argv) == 2 and (sys.argv[1] == '-f' or sys.argv[1] == '-force'):
        force()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testcicuit':
        test_circuit()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testvalve':
        test_valve()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testnotify':
        test_notify()
    elif len(sys.argv) == 2 and sys.argv[1] == '-testweather':
        test_weather()