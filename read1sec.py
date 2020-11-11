import time
import board
import busio
import adafruit_sht31d
import datetime as dt
import logging
import configparser
import sys
import math
import os
import schedule
import RPi.GPIO as GPIO
#from adafruit_seesaw.seesaw import Seesaw
from decimal import *
from subprocess import check_output
from influxdb import InfluxDBClient

def setupLogging():
    global logger
    try:
        logger = logging.getLogger()
        handler = logging.FileHandler('/home/pi/Desktop/growPi.log', 'a+')
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    except Exception as e:
        print("Logging failed to start: " + str(e))
    else:
        return str("ok")
        
def shipEnviroData(grafTemp, grafHum, grafvpd, graffan, grafheat, grafhumi):
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
                    "1.01" : grafTemp,
                    "2.01": grafHum,
                    "3.01": grafvpd,
                    "11.01": graffan,
                    "12.01": grafhumi,
                    "13.01": grafheat
                }
            }
        ]
        client.write_points(enviroData, time_precision='ms')
    except Exception as e:
        logger.debug("Cannot ship data to grafana: "+str(e))

def setupGPIO():
    try:
        GPIO.setmode(GPIO.BCM)
        #Outlet 1 (exhaust fan), 2 (not in use), 3 (humidifier) , 4 (heater)
        chan_list = [27,22,17,4]
        GPIO.setup(chan_list, GPIO.OUT)
        #1 is off, 0 is on
        GPIO.output(chan_list, 1)
    except Exception as e:
        logger.debug("GPIO setup failed: " + str(e))
    else:
        return str("ok")
        
def fanon():
    global fanoncycles, relaytype
    try:
        if relaytype == "wemo":
            check = check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo switch fan on",shell=True)
        elif relaytype == "wired":
            GPIO.output(27,0)
        fanoncycles += 1
        logger.debug("Fan turned on. Count: "+str(fanoncycles))
    except Exception as e:
        logger.debug("Could not turn on fan: "+str(e))
        
def fanoff():
    global fanoffcycles, relaytype
    try:
        if relaytype == "wemo":
            check = check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo switch fan off",shell=True)
        elif relaytype == "wired":
            GPIO.output(27,1)
        fanoffcycles += 1
        logger.debug("Fan turned off. Count: "+str(fanoffcycles))
    except Exception as e:
        logger.debug("Could not turn fan off: "+str(e))
        
def humidifieron():
    global humidifieroncycles, relaytype
    try:
        if relaytype == "wemo":
            check = check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo switch humidifier on",shell=True)
        elif relaytype == "wired":
            GPIO.output(17,0)
        humidifieroncycles += 1    
        logger.debug("Humidifier turned on. Count: "+str(humidifieroncycles))
    except Exception as e:
        logger.debug("Could not turn humidifier on: "+str(e))

def humidifieroff():
    global humidifieroffcycles, relaytype
    try:
        if relaytype == "wemo":
            check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo switch humidifier off",shell=True)
        elif relaytype == "wired":
            GPIO.output(17,1)
        humidifieroffcycles += 1
        logger.debug("Humidifier turned off. Count: "+str(humidifieroffcycles))
    except Exception as e:
        logger.debug("Could not turn humidifier off: "+str(e))
        
def heateron():
    global heateroncycles, relaytype
    try:
        if relaytype == "wemo":
            check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo switch 'heater bud 1' on",shell=True)
        elif relaytype == "wired":
            GPIO.output(4,0)
        heateroncycles += 1
        logger.debug("Heater turned on. Count: "+str(heateroncycles))
    except Exception as e:
        logger.debug("Could not turn heater on: "+str(e))
        
def heateroff():
    global heateroffcycles, relaytype
    try:
        if relaytype == "wemo":
            check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo switch 'heater bud 1' off",shell=True)
        if relaytype == "wired":
            GPIO.output(4,1)
        heateroffcycles += 1
        logger.debug("Heater turned off. Count: "+str(heateroffcycles))
    except Exception as e:
        logger.debug("Could not turn heater off: "+str(e))
        
def gettemp():
    #Get current temperature
    try:
        temp = round(sensor.temperature,1)
    except Exception as e:
        logger.debug("Could not get temperature: "+str(e))
        exit()
    else:
        return round(Decimal(temp),2)
        
def gethum():
    #Get current humidity
    try:
        humidity = round(sensor.relative_humidity,1)
        return round(Decimal(humidity),2)
        exit()
    except Exception as e:
        logger.debug("Could not get humidity: "+str(e))
        
def checkfan():
    global relaytype
    try:
        if relaytype == "wemo":
            check = check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo -v switch fan status",shell=True)
            return str(check)
        elif relaytype == "wired":
            pinstate = GPIO.input(27)
            if pinstate == 0:
                return "on"
            elif pinstate == 1:
                return "off"
    except Exception as e:
        logger.debug("Could not get fan status: "+str(e))
        
def checkhumidifier():
    global relaytype
    try:
        if relaytype == "wemo":
            check = check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo -v switch humidifier status",shell=True)
            return str(check)
        elif relaytype == "wired":
            pinstate = GPIO.input(17)
            if pinstate == 0:
                return "on"
            elif pinstate == 1:
                return "off"
    except Exception as e:
        logger.debug("Could not get humidifier status: "+str(e))
        
def checkheater():
    global relaytype
    try:
        if relaytype == "wemo":
            check = check_output("/usr/local/PotPi/env/bin/python3 /usr/local/PotPi/env/bin/wemo -v switch 'heater bud 1' status",shell=True)
            return str(check)
        elif relaytype == "wired":
            pinstate = GPIO.input(4)
            if pinstate == 0:
                return "on"
            elif pinstate == 1:
                return "off"
    except Exception as e:
        logger.debug("Could not get heater status: "+str(e))
        
def cure():
        global humidity, curehumhigh, curehumlow, humidifierstatus, humidifieroffcycles, humidifieroncycles, temp, curetemphigh, fanstatus, fanoncycles, curetemplow, templow, fanoffcycles, coldprotecttriggered, coldprotecttemp, heaterstatus

        logger.debug("Cure humidity adjustment:")
        if humidity >= curehumhigh:
            if "on" in humidifierstatus:
                logger.debug("Humidity is "+str(humidity)+", turning humidifier off.")
                humidifieroff()
            elif "off" in humidifierstatus:
                logger.debug("Humidifier is off already")
            #if "off" in fanstatus:
            #        if humidity > 52.0:
            #            logger.debug("Humidity is "+str(humidity)+", turning fan on.")
            #            fanon()
        if humidity <= (curehumlow):
            if "off" in humidifierstatus:
                logger.debug("Humidity is "+str(humidity)+", turning humidifier on.")
                humidifieron()
            elif "on" in humidifierstatus:
                logger.debug("Humidifier is on already.")
            if "on" in fanstatus:
                if temp < 16:
                    logger.debug("Humidity is "+str(humidity)+", turning fan off.")
                    fanoff()

        fanstatus = checkfan()
        humidifierstatus = checkhumidifier()
        heaterstatus = checkheater()
        logger.debug("Cure temperature adjustment:")
        if temp >= curetemphigh:
            if "off" in fanstatus:
            #    if temp > 26:
                 logger.debug("Temperature is "+str(temp)+", turning fan on.")
                 fanon()
            elif "on" in fanstatus:
                 logger.debug("Fan is on already.")
            if "on" in heaterstatus:
                logger.debug("Turning heater off.")
                heateroff()

        elif temp <= curetemplow:
            if "on" in fanstatus:
                if humidity < curehumhigh:
                    logger.debug("Temperature is "+str(temp)+", turning fan off.")
                    fanoff()
            elif  "off" in fanstatus:
                logger.debug("Fan is off already.")
            else:
                logger.debug(type(fanstatus))
                logger.debug("Fan status is "+fanstatus)
            if "off" in heaterstatus:
                if temp <= (curetemplow):
                    logger.debug("Turning heater on.")
                    heateron()
                    
def calcVPD():
    global temp, humidity, vpd
    try:
        ftemp=float(temp)
        #logger.debug("Temp: " + str(ftemp))
        fhumidity=float(humidity)
        #logger.debug("Hum: " + str(fhumidity))
        VPsat = 610.78*(2.71828**(ftemp/(ftemp+238.3)*17.2694))
        #logger.debug("VPSat: " +str(VPsat))
        vpd = (((100.0 - fhumidity) /100.0)/10 * VPsat)/100 # Vapor Pressure Deficit in Pascals
        logger.debug("Calculated VPD: "+str(round(Decimal(vpd),2)))
    except Exception as e:
        logger.debug("Could not calculate VPD: "+str(e))
    else:
        return vpd
        
def setupI2C():
    global i2c
    # set up i2c connections
    try:
    #connect i2c bus 1
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
    #connect i2c bus 3
       # i2c3 = busio.I2C(board.D17, board.D4)
    except Exception as e:
        logger.debug("Could not get i2c bus: "+str(e))
    else:
        return str("ok")
        
def connectSensors():
    global sensor, ss
    #Connect to sensors
    try:
        #Temp/humidity sensor
        sensor = adafruit_sht31d.SHT31D(i2c,0x45)
        #Soil sensors
        #ss.insert(0, Seesaw(i2c, addr=0x36))
        #ss.insert(1, Seesaw(i2c, addr=0x37))
        #ss.insert(2, Seesaw(i2c3, addr=0x36))
        #ss.insert(3, Seesaw(i2c3, addr=0x37))
    except Exception as e:
        logger.debug("Could not get SHT31-D Temp/Humidity or soil sensors: "+str(e))
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
        client = InfluxDBClient(host, port, user, password, dbname, False, False, 2)
    except Exception as e:
        logger.debug("Could not connect to InfluxDB for data tracking: "+ str(e))
    else:
        return str("ok")

def getsoilmoisture(i):
    global ss
    try:
        #get moisture
        sens = ss[i].moisture_read()
    except Exception as e:
        logging.debug("Could not get temperature from Sensor "+str(i)+": "+str(e))
    else:
        return sens

def getsoiltemp(i):
    global ss
    try:
        #read temperature from the temperature sensor
        temp = ss[i].get_temp()
    except Exception as e:
        logging.debug("Could not get moisture reading from Sensor "+str(i)+": "+str(e))
    else:
        return temp

def readconfig():
    global nighttemphigh, nighttemplow, nighthumhigh, nighthumlow, temphigh, templow, humhigh, humlow, coldprotecttemp, sleeptime, vpdset, nightvpdset, starthr, startmin, stophr, stopmin
    try:
        config = configparser.ConfigParser()
        config.read('/usr/local/PotPi/bin/config.ini')
        starthr = Decimal(config['DEFAULT']['STARTHR'])
        startmin = Decimal(config['DEFAULT']['STARTMIN'])
        stophr = Decimal(config['DEFAULT']['STOPHR'])
        stopmin = Decimal(config['DEFAULT']['STOPMIN'])
        temphigh = Decimal(config['DEFAULT']['HIGHTEMP']) #28.0
        templow = Decimal(config['DEFAULT']['LOWTEMP']) #25.0
        humhigh = Decimal(config['DEFAULT']['HIGHHUM']) #40.0
        humlow = Decimal(config['DEFAULT']['LOWHUM']) #30.0
        nighttemphigh = Decimal(config['DEFAULT']['NIGHTHIGHTEMP']) #28.0
        nighttemplow = Decimal(config['DEFAULT']['NIGHTLOWTEMP']) #25.0
        nighthumhigh = Decimal(config['DEFAULT']['NIGHTHIGHHUM']) #40.0
        nighthumlow = Decimal(config['DEFAULT']['NIGHTLOWHUM']) #30.0
        sleeptime = Decimal(config['DEFAULT']['SLEEPTIME']) #1
        coldprotecttemp = Decimal(config['DEFAULT']['COLDPROTECTTEMP']) #15.0
        honcount = Decimal(config['DEFAULT']['HONCOUNT'])
        hoffcount = Decimal(config['DEFAULT']['HOFFCOUNT'])
        humoncount = Decimal(config['DEFAULT']['HUMONCOUNT'])
        humoffcount = Decimal(config['DEFAULT']['HUMOFFCOUNT'])
        fanoncount = Decimal(config['DEFAULT']['FANONCOUNT'])
        fanoffcount = Decimal(config['DEFAULT']['FANOFFCOUNT'])
        vpdset = Decimal(config['DEFAULT']['VPD'])
        nightvpdset = Decimal(config['DEFAULT']['NIGHTVPD'])
    except Exception as e:
        logger.debug("Could not read configuration: "+str(e))
        exit()

def fixvpd():
    global vpd, t, vpdset, nightvpdset
#day
    if when == True:
        logger.debug("Day VPD adjustment")
        if vpd < vpdset:
            logger.debug("VPD below target")
            #if "on" in humidifierstatus:
               # logger.debug("turning humidifier off.")
                #humidifieroff()
            if "off" in fanstatus:
                logger.debug("Turning fan on")
                fanon()
        elif vpd > vpdset:
            logger.debug("VPD above target")
            #if "off" in humidifierstatus:
                #logger.debug("turning humidifier on.")
                #humidifieron()
            if "on" in fanstatus:
                logger.debug("turning fan off.")
                fanoff()
#night
    elif when == False:
        logger.debug("Night VPD adjustment")
        if vpd < nightvpdset:
            logger.debug("VPD below target")
            if "off" in fanstatus:
                #if humidity > nighthumhigh:
                logger.debug("Humidity is "+str(humidity)+", turning fan on.")
                fanon()
            if "on" in humidifierstatus:
                logger.debug("Humidifier turned off")
                humidifieroff()

        elif vpd > nightvpdset:
            logger.debug("VPD above target")
            if "on" in fanstatus:
                #if humidity > nighthumhigh:
                logger.debug("Humidity is "+str(humidity)+", turning fan off.")
                fanoff()
            #if "off" in humidifierstatus:
                #logger.debug("Humidifier turned on")
                #humidifieron()

def fixtemp():
    global temp, temphigh, nighttemphigh, fanstatus, fanoncycles, templow, nighttemplow, fanoffcycles, coldprotecttriggered, coldprotecttemp, when, heaterstatus
    if temp <= coldprotecttemp:
        try:
            if "off" in heaterstatus:
                logger.debug("Temperature has fallen below Cold Protect temperature of "+str(coldprotecttemp)+", turning heater on.")
                heateron()
                coldprotecttriggered = 1
                return
        except Exception as e:
            logger.debug("Could not turn on heater for cold protection: "+str(e))
    if when == False:
#Night
        logger.debug("Night temp adjustment:")
        if temp >= (nighttemphigh):
            if "on" in heaterstatus:
                logger.debug("Temperature is "+str(temp)+", turning heater off.")
                heateroff()
            elif "off" in heaterstatus:
                logger.debug("Temp is above High Temp setting. Heater is off already.")
                #if "off" in fanstatus:
                    #fanon()
        elif temp <= (nighttemplow):
            #if "on" in fanstatus:
               # fanoff()
            if "off" in heaterstatus:
                logger.debug("Temperature is "+str(temp)+", turning heater on.")
                heateron()
            elif  "on" in heaterstatus:
                logger.debug("Temp is below Low Temp setting. Heater is on already.")
        if coldprotecttriggered == 1:
            if temp >= nighttemphigh:
                try:
                    if "on" in heaterstatus:
                        logger.debug("Temperature has recovered to High Temperature setting. Turning heater off.")
                        heateroff()
                        coldprotecttriggered = 0
                except Exception as e:
                    logger.debug("Could not turn off heater to exit cold protection: "+str(e))

    elif when == True:
#Day
        logger.debug("Day temp adjustment:")
        if temp >= temphigh:
            if "off" in fanstatus:
                logger.debug("Temperature is "+str(temp)+", turning fan on.")
                fanon()
            elif "on" in fanstatus:
                logger.debug("Temp is above High Temp setting. Fan is on already.")
            if "on" in heaterstatus:
                logger.debug("Turning heater off.")
                heateroff()
        elif temp < templow:
            if "on" in fanstatus:
                if vpd <= vpdset:
                    logger.debug("Temperature is "+str(temp)+", turning fan off.")
                    fanoff()
            elif  "off" in fanstatus:
                logger.debug("Temp is below Low Temp setting. Fan is off already.")
            if "off" in heaterstatus:
                logger.debug("Turning heater on.")
                heateron()
        if coldprotecttriggered == 1:
            if temp >= templow:
                try:
                    heaterstatus = checkheater()
                    if "on" in heaterstatus:
                        logger.debug("Temperature has recovered to Low Temperature setting. Turning heater off.")
                        heateroff()
                        coldprotecttriggered = 0
                except Exception as e:
                    logger.debug("Could not turn off heater to exit cold protection: "+str(e))

def fixhum():
    global humidity, humhigh, nighthumhigh, humlow, nighthumlow, humidifierstatus, humidifieroffcycles, humidifieroncycles, when, heaterstatus, fanstatus
    if when == False:
#Night
        logger.debug("Night hum adjustment:")
        #if humidity >= nighthumhigh:
        #    if "on" in humidifierstatus:
        #        logger.debug("Humidity is "+str(humidity)+", turning humidifier off.")
        #        humidifieroff()
        #    if "off" in fanstatus:
        #        if humidity > nighthumhigh:
        #            logger.debug("Humidity is "+str(humidity)+", turning fan on.")
        #            fanon()
        #    elif "on" in fanstatus:
        #        if humidity < nighthumhigh:
        #            logger.debug("Humidity is "+str(humidity)+", turning fan off.")
        #            fanoff()
        if humidity > nighthumhigh:
            if "off" in fanstatus:
                fanon()
        elif humidity < nighthumhigh:
            if "on" in fanstatus:
                fanoff()


#        if humidity <= nighthumlow:
 #           if "off" in humidifierstatus:
  #              logger.debug("Humidity is "+str(humidity)+", turning humidifier on.")
   #             humidifieron()
    #        if "on" in humidifierstatus:
     #           logger.debug("Humidifier is on already.")
      #      if "on" in fanstatus:
       #         logger.debug("Turning fan off.")
        #        fanoff()

    elif when == True:
#Day
        logger.debug("Day hum adjustment:")
        if humidity > humhigh:
            if "off" in fanstatus:
                fanon()
        elif humidity < humhigh:
            if temp < temphigh:
                if "on" in fanstatus:
                    fanoff()

#        if humidity >= humhigh:
 #           if "on" in humidifierstatus:
  #              logger.debug("Humidity is "+str(humidity)+", turning humidifier off.")
   #             humidifieroff()
    #        elif "off" in humidifierstatus:
     #           logger.debug("Humidifier is off already")
      #  if humidity <= humlow:
#            if "off" in humidifierstatus:
 #               logger.debug("Humidity is "+str(humidity)+", turning humidifier on.")
  #              humidifieron()
   #         elif "on" in humidifierstatus:
    #            logger.debug("Humidifier is on already.")
    elif 1 == 2:
        logger.debug("function cap")

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

def getsoilinfo(i):
    try:
        ssm = getsoilmoisture(i)
        sst = getsoiltemp(i) 
        logger.debug("Soil "+str(i)+" Moisture: "+str(ssm)+" Temp: "+str(round(Decimal(sst),2)))
    except Exception as e:
        logger.debug("Could not read soil moisture/temp sensor "+str(i)+": "+str(e))
             
####INITIALIZATION####
#parameters:
curehumhigh = 55.0
curehumlow = 53.0
curetemphigh = 21.0
curetemplow = 20.5
loopcount = 0
fanoncycles = 0
fanoffcycles = 0
humidifieroncycles = 0
humidifieroffcycles = 0
heateroncycles = 0
heateroffcycles = 0
humidifierstatus = "not set"
fanstatus = "not set"
heaterstatus = "not set" 
coldprotecttriggered = 0    
starthr = 6# before midnight
startmin = 00
stophr = 23 # after midnight
stopmin = 59
vpdset = 1.55 #set default value
nightvpdset = 1.0 #set default value
sleeptime = 5
coldprotecttemp = 16.0
relaytype = "wired"
ss = []

#Set up logging
logger = ""
if setupLogging() == "ok":
    logger.debug("Script started.")
    
    #Configure GPIO if relays are wired
    if relaytype == "wired":
        logger.debug("Setting up GPIO.")
        setupGPIO()
            
    #I2C connectivity
    i2c = ""
    logger.debug("Connecting I2C.")
    if setupI2C() == "ok":
        #Temp/Humidity sensor
        sensor = ""
        logger.debug("Connecting sensors")
        if connectSensors() == "ok":
            #InfluxDB Client
            client = ""
            logger.debug("Connecting InfluxDB")
            if setupInfluxDB() == "ok":
                logger.debug("Reading config from config.ini")
                readconfig()
                ####MAIN LOOP####
                logger.debug("Running main program")
                while True:
                    try:
                        #time.sleep(60)
                        logger.debug("\r")
                        when = checktime(starthr,startmin,stophr,stopmin)
                        if when == False:
                            logger.debug("Night time detected.")
                        elif when == True:
                            logger.debug("Day time detected.")
                        temp = gettemp()
                        humidity = gethum()
                        fanstatus = checkfan()
                        humidifierstatus = checkhumidifier()
                        heaterstatus = checkheater()
                        #getsoilinfo(0)
                        #getsoilinfo(1)
                        #getsoilinfo(2)
                        #getsoilinfo(3)
                        #ssm0 = getsoilmoisture(0)
                        #ssm1 = getsoilmoisture(1)
                        #ssm2 = getsoilmoisture(2)
                        #ssm3 = getsoilmoisture(3)
                        #if ssm0 > 2000:
                            #ssm0=0
                        #if ssm1 > 2000:
                            #ssm1=0
                        #if ssm2 > 2000:
                            #ssm2=0
                        #if ssm3 > 2000:
                            #ssm3=0
                        if "on" in fanstatus:
                            graffan = "1"
                        elif "off" in fanstatus:
                            graffan = "0"
                        else:
                            graffan = "-1"
                        humidifierstatus = checkhumidifier()
                        if "on" in humidifierstatus:
                            grafhumi = "1"
                        elif "off" in humidifierstatus:
                            grafhumi = "0"
                        else:
                            grafhumi = "-1"

                        heaterstatus = checkheater()
                        if "on" in heaterstatus:
                            grafheat = "1"
                        elif "off" in heaterstatus:
                            grafheat = "0"
                        else:
                            grafheat = "-1"
                        logger.debug("Temperature: "+str(temp))
                        logger.debug("Humidity: "+str(humidity))
                        calcVPD()
                        #shipEnviroData(float(temp),float(humidity),float(vpd),0.00,0.00,0.00)
                        shipEnviroData(float(temp),float(humidity),float(vpd),float(graffan), float(grafheat), float(grafhumi))
                        fixtemp()
                        fixvpd()
                        #fixhum()
                        #cure()
                        loopcount += 1
                        time.sleep(int(sleeptime))
                    except Exception as e:
                        logger.debug("Loop failed: "+str(e))
