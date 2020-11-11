import time
import logging
import configparser
import sys
import math
import os
import schedule
import RPi.GPIO as GPIO
from decimal import *
from influxdb import InfluxDBClient
import functools

def catch_exceptions(cancel_on_failure=False):
    def catch_exceptions_decorator(job_func):
        @functools.wraps(job_func)
        def wrapper(*args, **kwargs):
            try:
                return job_func(*args, **kwargs)
            except:
                import traceback
                print(traceback.format_exc())
                if cancel_on_failure:
                    return schedule.CancelJob
        return wrapper
    return catch_exceptions_decorator

def setupGPIO():
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(22, GPIO.OUT)
        GPIO.output(22,1)
    except Exception as e:
        logger.debug("Could not set up GPIO: "+str(e))
        exit()
    else:
        return str("ok")

def setupLogging():
    global logger
    try:
        logger = logging.getLogger()
        handler = logging.FileHandler('/home/pi/Desktop/growPi-Watering.log', 'a+')
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    except Exception as e:
        print("Logging failed to start: " + str(e))
    else:
        return str("ok")
        
@catch_exceptions(cancel_on_failure=True)
def shipEnviroData(grafWater):
    global sensortype

    try:
        iso = time.ctime()
        # Create the JSON data structure
        enviroData = [
            {
                "measurement": "rpi-sht-31d",
                "tags": {
                    "sensortype": "environmental",
                },
                "time": iso,
                "fields": {
                    "1.07" : grafWater
                }
            }
        ]
        client.write_points(enviroData, time_precision='ms')
    except Exception as e:
        logger.debug("Cannot ship data to grafana: "+str(e))
    else:
        return str("ok")

@catch_exceptions(cancel_on_failure=True)
def wateron():
    try:
        iso = time.ctime()
        # Create the JSON data structure
        grafWater = 1
        try:
            GPIO.output(22,0)
        except Exception as e:
            logger.debug("Could not turn on water: " + str(e))
        else:        
            logger.debug("Water turned on.")
            shipEnviroData(grafWater)
    except Exception as e:
        logger.debug("Could not turn water on: " + str(e))
    else:
        return str("ok")
        
@catch_exceptions(cancel_on_failure=True)
def wateroff():
    try:
        iso = time.ctime()
        # Create the JSON data structure
        grafWater = 0
        try:
            GPIO.output(22,1)
        except Exception as e:
            logger.debug("Could not turn off water: " + str(e))
        else:
            logger.debug("Water turned off.")
            shipEnviroData(grafWater)
    except Exception as e:
        logger.debug("Could not turn water off: " + str(e))
    else:
        return str("ok")

@catch_exceptions(cancel_on_failure=True)
def water():
    global relaytype, wateringtime
    try:
        if relaytype == "wired":
            if wateron() == "ok":
                time.sleep(wateringtime)
                wateroff()
    except Exception as e:
        logger.debug("Cannot water: "+str(e))
    else:
        return str("ok")

def setupInfluxDB():
    global client
    try:
        # Configure InfluxDB connection variables
        host = "10.0.0.13" # My Ubuntu NUC
        port = 8086 # default port
        user = "rpi-3" # the user/password created for the pi, with write access
        password = "data@LOG" 
        dbname = "sensor_data" # the database we created earlier
        # Create the InfluxDB client object
        client = InfluxDBClient(host, port, user, password, dbname)
    except Exception as e:
        logger.debug("Could not connect to InfluxDB for data tracking: "+ str(e))
    else:
        return str("ok")
        
def readconfig():
    global wateringtime
    try:
        config = configparser.ConfigParser()
        config.read('/usr/local/PotPi/bin/config.ini')
        wateringtime = Decimal(config['DEFAULT']['WATERINGTIME']) #90 seconds
    except Exception as e:
        logger.debug("Could not read configuration: "+str(e))
        exit()
    else:
        return str("ok")
         
def mainprog():
    try:
        schedule.run_pending()
        time.sleep(int(sleeptime))
    except Exception as e:
        logger.debug("Loop failed: "+str(e))
    else:
        return str("ok")

####INITIALIZATION####
#parameters:
wateringtime = 90
sleeptime = 900

schedule.every().day.at("08:30").do(water)
schedule.every().day.at("21:30").do(water)


#Set up logging
logger = ""
relaytype="wired"

if setupLogging() == "ok":
    logger.debug("Script started.")
    #InfluxDB Client
    client = ""
    logger.debug("Connecting InfluxDB")
    if setupInfluxDB() == "ok":
        logger.debug("Reading config from config.ini")
        if readconfig() == "ok":
            if relaytype == "wired":
                if setupGPIO() == "ok":
                    logger.debug("Running main program")
                    while True:
                        run = mainprog()
                        if run == "ok":
                            logger.debug(".")
                        else:
                            logger.debug("Exiting.")
                            exit()

