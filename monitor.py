#! /usr/bin/python

# Axpert Inverter control script

# Read values from inverter, sends values to MQTT broker,
# calculation of CRC is done by XMODEM mode, but in firmware is wierd mistake in POP02 command, so exception of calculation is done in serial_command(command) function

import time, sys, string
import os
import crcmod
import paho.mqtt.client as mqtt
import sqlite3
import json
import datetime
import calendar
import fcntl
import re
import crcmod
import logging
from binascii import unhexlify
from random import randint

############create function for mqtt subscribe callback
def on_message(client, userdata, message):  
    print("message received " ,str(message.payload.decode("utf-8")))
    axpertSendCmd(str(message.payload.decode("utf-8"))) #send command to axpert inverter when topic recieved
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)

########################################create function for mqtt publish callback
def on_publish(client,userdata,result): #create function for callback
    print("data published \n")
    print("message published " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)
    pass

########################################function to send command to axpert inverter
def axpertSendCmd(command):
    if command == 'PV':
        print('Switching inverter to solar charging')
    elif command == 'LINE':
        print('Switching inverter to grid charging')

############runs when mqtt connect 
def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True #set flag
        logging.info(str(datetime.datetime.now()) + "mqtt connected OK Returned code=" + str(rc))
        #client.subscribe(topic)
    else:
        client.bad_connection_flag=True #set flag to indicate problem with connection
        logging.warning(str(datetime.datetime.now()) + "mqtt NOT connected Returned code=" + str(rc))
        
############connect to mqtt broker
def mqtt_connect():
    global client
    mqtt.Client.connected_flag=False        #create flag in class
    mqtt.Client.bad_connection_flag=False   #create flag in class
    
    client = mqtt.Client(client_id=os.environ['MQTT_CLIENT_ID']+str(randint(100000,999999)))
    client.on_message=on_message #attach function to subscribe callback
    client.on_publish = on_publish #attach function to publish callback
    client.on_connect = on_connect #attach function to connect callback
    client.username_pw_set(os.environ['MQTT_USER'], os.environ['MQTT_PASS'])

    try:
##        client.loop_start()    #start mqtt loop to receive messages
        client.connect(os.environ['MQTT_SERVER'], keepalive=30)
    except Exception as e:
        logging.warning(str(datetime.datetime.now()) + "MQTT connection error" + str(e))
        return 0

    client.loop_start()        
    while not client.connected_flag and not client.bad_connection_flag: #wait in loop
        time.sleep(1)    

    if client.bad_connection_flag:
        return 0
    if client.connected_flag:
        return 1

############Open and close USB serial port
def open_port():
    try:            # try to open serial port then close it
        fd = open('/dev/hidraw0', 'rb+')
        time.sleep(2)
        fd.close()
    except Exception as e:
        logging.warning(str(datetime.datetime.now()) + "Error opening USB port" + str(e))
        return 0
    return 1

############close USB serial port
def disconnect():
    #file.close()
    fd.close()      #   close serial port

############send command to axpert inverter and read response
def serial_command(command):
##    print(command)
    try:
        response = ''
        xmodem_crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)
        def calc_crc(command):
            global crc
            crc = hex(xmodem_crc_func(command))
            return crc

        if command == 'QPIGS':  #Device general status parameters inquiry
            nbytes = 110
        elif command == 'QID':  #Device serial number inquiry
            nbytes = 18
        elif command == 'QFLAG':    #Device flag status inquiry
            nbytes = 15
        elif command == 'QPI':  #Device protocol ID inquiry
            nbytes = 8
        elif command == 'QMOD': #Device mode inquiry
            nbytes = 5
        else:
            response = ''
            print('Command not found')
            return


        calc_crc(command.encode('ISO-8859-1'))  #   return crc variable

        crc1=crc[0:4]
        crc2=crc[0:2]+crc[4:6]

        crc1=int(crc1, base=16)
        crc2=int(crc2, base=16)

        scomm = command+chr(crc1)+chr(crc2)+'\r'
        bcomm = scomm.encode('ISO-8859-1')        

        try:
            fd = open('/dev/hidraw0', 'rb+')    #   open serial port
            fd.write(bcomm)                     #   send command to serial port
            r = fd.read(nbytes)                 #   read response from serial port
        except Exception as e:
            logging.warning(str(datetime.datetime.now()) + "Error communicating with USB port " + str(e))
            return 'USB Error'

        fd.close()  #   close serial port

        response = str(r)
        response = response.rstrip()    #   strip trailing spaces
        lastI = response.find('\r')     
        response = response[3:lastI-10] # cut off b'( and a\xc8\r
        return response

    except Exception as e:
        logging.warning(str(datetime.datetime.now()) + "Error communicating with inverter " + str(e))
        fd.close()
        time.sleep(0.1)
        response = ''
        return


############
def get_data_QPIGS():   #collect data from axpert inverter
    try:
        command = 'QPIGS'
        response = serial_command(command)
        if response == 'USB Error':
            return ''
        #response='(232.0 50.1 232.0 50.1 0000 0000 000 476 27.02 000 100 0553 0000 000.0 27.00 00000 10011101 03 04 00000 101a\xc8   QPIGS
        #print('QPIGS='+response)
        qpigs = response.split(' ')
        #print(qpigs)
        #if len(nums) < 21:
        #    return ''
        #['234.0', '50.0', '234.0', '50.0', '0000', '0000', '000', '476', '26.99', '000', '100', '0536', '0000', '000.0', '27.00', '00000', '10011101', '03', '04', '00000', '']

        data = '"GridVoltage":' + str(float(qpigs[0]))
        data += ',"GridFrequency":' + str(float(qpigs[1]))
        data += ',"ACOutputVoltage":' + str(float(qpigs[2]))
        data += ',"ACOutputFrequency":' + str(float(qpigs[3]))
        data += ',"ACOutputApparentPower":' + str(int(qpigs[4]))
        data += ',"ACOutputActivePower":' + str(int(qpigs[5]))
        data += ',"OutputLoadPercent":' + str(int(qpigs[6]))
        data += ',"BusVoltage":' + str(int(qpigs[7]))
        data += ',"BatteryVoltage": ' + str(float(qpigs[8]))
        data += ',"BatteryChargingCurrent":' + str(int(qpigs[9]))
        data += ',"BatteryCapacity":' + str(int(qpigs[10]))
        data += ',"DeviceStatus":"' + str(qpigs[16]) + '"'

        return data
    except Exception as e:
        logging.warning(str(datetime.datetime.now()) + "Error parsing QPIGS inverter data " + str(e))
        return ''

############
def get_data_QMOD():
    #collect data from axpert inverter
    try:
        command = 'QMOD'
        qmod = serial_command(command)
        if qmod == 'USB Error':
            return ''
        #P Power on mode
        #S Standby mode
        #L Line Mode
        #B Battery mode
        #F Fault mode
        #H Power saving Mode 

        #print('QMOD='+response)
        #qmod = response #.split(' ')

        #print('QMOD='+qmod)
        #(L<CRC><cr> 
        
        data = '"Mode":"' + qmod + '"'
        return data
    except Exception as e:
        logging.warning(str(datetime.datetime.now()) + "Error parsing QMOD inverter data " + str(e))
        return ''


###########publish data to mqtt broker
def send_data(data, topic):
    #print(topic + ' ' + data)
    try:
        client.publish(topic, data, qos=2, retain=1)
        time.sleep(2)
    except Exception as e:
        print('error sending to mqtt broker...: ' + str(e))
        return 0
    return 1

############
def main():
    numeric_level = getattr(logging, os.environ['LOGGING_LEVEL'].upper(), None)
    if not isinstance(numeric_level, int):
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=numeric_level)
    
    logging.info(str(datetime.datetime.now()) + ' Startup')  # will print a message to the console
    
    counter=0
    while True:
        if counter == 10:
            logging.warning(str(datetime.datetime.now()) + ' Unable to connect to mqtt broker' + os.environ['MQTT_SERVER'])
            sys.exit()

        response = mqtt_connect()  #connect to MQTT broker

        if not response:
            logging.warning(str(datetime.datetime.now()) + " mqtt connection error")
            counter+=1
            time.sleep(1)
        else:
            logging.info(str(datetime.datetime.now()) + " mqtt connection success")
            break
    interval = int(os.environ['INTERVAL'])

    response = open_port()  #open and close USB serial port
    time.sleep(2)
    if not response:
        logging.warning(str(datetime.datetime.now()) + " error opening USB serial port")
        sys.exit()          #could not read USB serial port so exit the program
    
    command = 'QID'         
    serial_number = serial_command(command)   #get serial number from inverter
    if serial_number == 'USB Error':
        logging.warning(str(datetime.datetime.now()) + " error reading serial number of inverter")

    qpigs_data = get_data_QPIGS()
    if qpigs_data == '':
        logging.warning(str(datetime.datetime.now()) + ' QPIGS no data')

    qmod_data = get_data_QMOD()
    if qmod_data == '':
        logging.warning(str(datetime.datetime.now()) + ' QMOD no data')

    axpert_data = '{' + '"SerialNumber":"' + str(interval) + '",' + qpigs_data + ',' + qmod_data + '}'

    send = send_data(axpert_data, os.environ['MQTT_TOPIC']) #publish data to mqtt broker
    if send == 1:
        logging.info(str(datetime.datetime.now()) + " MQTT publish:" + axpert_data)
    elif send == 0:
        logging.warning(str(datetime.datetime.now()) + " MQTT publish error:"  + axpert_data)

    timer = 0

    while True:
        time.sleep(1)
        timer += 1

        if timer == interval: #every x seconds query inverter for data
            qpigs_data = get_data_QPIGS()
            if qpigs_data == '':
                logging.warning(str(datetime.datetime.now()) + ' QPIGS no data')
            qmod_data = get_data_QMOD()
            if qmod_data == '':
                logging.warning(str(datetime.datetime.now()) + ' QMOD no data')

            #   build string with all inverter data
            axpert_data = '{' + '"SerialNumber":"' + str(serial_number) + '",' + qpigs_data + ',' + qmod_data + '}'

            send = send_data(axpert_data, os.environ['MQTT_TOPIC']) #publish data to mqtt broker
            if send == 1:
                logging.info(str(datetime.datetime.now()) + " MQTT publish:" + axpert_data)
            elif send == 0:
                logging.warning(str(datetime.datetime.now()) + " MQTT publish error:" + axpert_data)
            time.sleep(2)
            timer = 0

############
if __name__ == '__main__':
    main()
