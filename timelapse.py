import time
import datetime as dt
import urllib.request
import logging
import configparser
import sys
import math
import os
import schedule
from decimal import *

####INITIALIZATION####
#parameters:
starthr = 21# before midnight
startmin = 00
stophr = 9 # after midnight
stopmin = 00
piccount = 0
oldinterval = ""
currentinterval = ""
picfoldername = dt.datetime.now().strftime("%Y-%m-%d")

def setupLogging():
    global logger
    try:
        logger = logging.getLogger()
        handler = logging.FileHandler('/home/pi/Desktop/growPi-Timelapse.log', 'a+')
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    except Exception as e:
        print("Logging failed to start: " + str(e))
    else:
        return str("ok")

def count_files(dir):
    return len([1 for x in list(os.scandir(dir)) if x.is_file()])

def makepicdir(folder):
    try:
        os.makedirs("/home/pi/Pictures/"+folder)
    except Exception as e:
        if str(e).__contains__("Errno 17"):
            logger.debug("Folder /home/pi/Pictures/"+folder+" already exists")
        else:
            logger.debug("Could not create picture folder: "+str(e))
    else:
        return str("ok")

def readconfig():
    global starthr, startmin, stophr, stopmin
    try:
        config = configparser.ConfigParser()
        config.read('/usr/local/PotPi/bin/config.ini')
        starthr = Decimal(config['DEFAULT']['STARTHR']) #1
        startmin = Decimal(config['DEFAULT']['STARTMIN']) #1
        stophr = Decimal(config['DEFAULT']['STOPHR']) #1
        stopmin = Decimal(config['DEFAULT']['STOPMIN']) #1
    except Exception as e:
        logger.debug("Could not read configuration: "+str(e))
        exit()
    else:
        return str("ok")

def takepic():
    if when == True: #Day
        global piccount, picfoldername
        #Take a picture if 5 minutes have passed
        try:
            logger.debug("Saving picture to /home/pi/Pictures/" + picfoldername)
            urllib.request.urlretrieve("http://192.168.0.90/axis-cgi/jpg/image.cgi?resolution=1280x720", "/home/pi/Pictures/"+picfoldername+"/"+str(piccount).zfill(3)+".jpg")
            piccount += 1
        except Exception as e:
            logger.debug("Could not take picture: "+str(e))
        else:
            return str("ok")


def checktime(starthour, startmin, stophour, stopmin):
    # Set the now time to an integer that is hours * 60 + minutes
    n = dt.datetime.now()
    curr = n.hour * 60 + n.minute 
     
    # Set the start time to an integer that is hours * 60 + minutes
    str = dt.time(starthour, startmin)
    start = str.hour * 60 + str.minute 
     
    # Set the stop time to an integer that is hours * 60 + minutes
    stp = dt.time(stophour, stopmin)
    stop = stp.hour * 60 + stp.minute


    if (start > stop):
        if (curr >= start) or (curr < stop):
            return True #day
        elif (curr < start) and (curr > stop):
            return False #night
    elif (start < stop):
        if (curr >= start) and (curr <stop):
            return True #day
        elif (curr < start) or (curr > stop):
            return False #night



def setupschedules():
    try:
        schedule.every(5).minutes.do(takepic)
    except Exception as e:
        logger.debug("Could not set up schedule: " +str(e))
    else:
        return str("ok")             

def checknewday(interval):
    global currentinterval, oldinterval
    oldinterval = currentinterval
    currentinterval = interval
    if oldinterval == False:
        if currentinterval == True:
            return str("newday")
    if oldinterval == "":
        return str("newday") #script start

#Set up logging
logger = ""
if setupLogging() == "ok":
    logger.debug("Script started.")
    logger.debug("Reading config from config.ini")
    if readconfig() == "ok":
        logger.debug("Configuration read")
        ####MAIN LOOP####
        logger.debug("Running main program")
        if setupschedules() == "ok":
            try:
                piccount = count_files("/home/pi/Pictures/"+picfoldername)
            except FileNotFoundError:
                logger.debug("Folder doesn't exist.")
                piccount = 0
            logger.debug("Starting picture count at "+str(piccount))
            while True:
                try:
                    when = checktime(starthr,startmin,stophr,stopmin)
                    newday = ""
                    newday = checknewday(when)
                    if newday == "newday":
                        picfoldername = dt.datetime.now().strftime("%Y-%m-%d")
                        if makepicdir(picfoldername) == "ok":
                            logger.debug("Made new day's folder: /home/pi/Pictures/"+picfoldername)
                            piccount = count_files("/home/pi/Pictures/"+picfoldername)
                            logger.debug("Reset picture count to "+str(piccount))
                    schedule.run_pending()
                    logger.debug(".")
                    time.sleep(30)
                except Exception as e:
                    logger.debug("Could not run main loop: " +str(e))
                    exit()
