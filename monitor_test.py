#! /usr/bin/python

# Axpert Inverter control script

# Read values from inverter, sends values to MQTT broker,
# calculation of CRC is done by XMODEM mode, but in firmware is weird mistake in POP02 command, so exception of calculation is done in serial_command(command) function

import time, sys, string
##import sqlite3
##import json
##import datetime
##import calendar
##import os
##import fcntl
##import re
##import crcmod
##from binascii import unhexlify
import paho.mqtt.client as mqtt
##from random import randint

############create function for mqtt subscribe callback
def on_message(client, userdata, message):  
    print("message received " ,str(message.payload.decode("utf-8")))
    axpertSendCmd(str(message.payload.decode("utf-8"))) #send command to axpert inverter when topic recieved
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)

########################################create function for mqtt publish callback
def on_publish(client,userdata,result): #create function for callback
    print("data publisheddd \n")
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
        print("mqtt connected OK Returned code=",rc)
        #client.subscribe(topic)
    else:
        client.bad_connection_flag=True #set flag to indicate problem with connection
        print("mqtt Bad connection Returned code= ",rc)
        
############Open and close USB serial port
def open_port():
    try:            # try to open serial port then close it
        fd = open('/dev/hidraw0', 'rb+')
        time.sleep(2)
        fd.close()
    except Exception as e:
        print('error opening USB port: ' + str(e))
        return 0
    return 1

############close USB serial port
def disconnect():
    #file.close()
    fd.close()      #   close serial port

############send command to axpert inverter and read response
def serial_command(command):
    print(command)
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
        print('Command='+str(command))
        print('CRC='+str(crc))

        crc1=crc[0:4]
        crc2=crc[0:2]+crc[4:6]

        crc1=int(crc1, base=16)
        crc2=int(crc2, base=16)

        scomm = command+chr(crc1)+chr(crc2)+'\r'
        print('scomm='+str(scomm))
        bcomm = scomm.encode('ISO-8859-1')        
        print('bcomm='+str(bcomm))

        try:
            fd = open('/dev/hidraw0', 'rb+')    #   open serial port
            fd.write(bcomm)                     #   send command to serial port
            r = fd.read(nbytes)                 #   read response from serial port
        except Exception as e:
            print('error communicating with USB port...: ' + str(e))
            return 'USB Error'

        print('r='+str(r)) 
        # r=b'(92332004101045\x14\xb2\r'
        #r=b'(232.0 50.1 232.0 50.1 0000 0000 000 476 27.02 000 100 0553 0000 000.0 27.00 00000 10011101 03 04 00000 101a\xc8\r'   QPIGS
        response = str(r)

        j = r.decode('ISO-8859-1') # j=(92332004101045²  QID
        print('j='+j)
        #j=(232.0 50.1 232.0 50.1 0000 0000 000 476 27.02 000 100 0553 0000 000.0 27.00 00000 10011101 03 04 00000 101aÈ   QPIGS

        s = j.split('\\') # splitting at \\
        print(j.split('\\')) #print('s'+s)
        #['(232.0 50.1 232.0 50.1 0000 0000 000 476 27.02 000 100 0553 0000 000.0 27.00 00000 10011101 03 04 00000 101aÈ\r']   QPIGS

        i = s[0][1:].split(" ")
        print(i)
        #['232.0', '50.1', '232.0', '50.1', '0000', '0000', '000', '476', '27.02', '000', '100', '0553', '0000', '000.0', '27.00', '00000', '10011101', '03', '04', '00000', '101aÈ\r']   QPIGS

        fd.close()  #   close serial port
        #print(response)
        response = response.rstrip()    #   strip trailing spaces
        lastI = response.find('\r')     
        response = response[3:lastI-10] # cut off b'( and a\xc8\r
        print('response='+response)
        #response='(232.0 50.1 232.0 50.1 0000 0000 000 476 27.02 000 100 0553 0000 000.0 27.00 00000 10011101 03 04 00000 101a\xc8   QPIGS
        return response
    except Exception as e:
        print('error reading inverter...: ' + str(e))
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
        print('QPIGS='+response)
        qpigs = response.split(' ')
        print(qpigs)
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
        print('error parsing QPIGS inverter data...: ' + str(e))
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

        print('QMOD='+qmod)
        #(L<CRC><cr> 
        
        data = '"Mode":"' + qmod + '"'
        return data
    except Exception as e:
        print('error parsing QMOD inverter data...: ' + str(e))
        return ''


###########publish data to mqtt broker
def send_data(data, topic):
    print(topic + ' ' + data)
    try:
        client.publish(topic, data) #, qos=2, retain=1)
        time.sleep(2)
    except Exception as e:
        print('error sending to mqtt broker...: ' + str(e))
        return 0
    return 1

############
def main():
    print('Let us Go!!')

    global client
    mqtt.Client.connected_flag=False        #create flag in class
    mqtt.Client.bad_connection_flag=False   #create flag in class
    
    client = mqtt.Client(client_id='axpert')
    client.on_message = on_message #attach function to subscribe callback
    client.on_publish = on_publish #attach function to publish callback
    client.on_connect = on_connect #attach function to connect callback
    client.username_pw_set('mqttuser', 'mqttpass')

    print("connecting to broker")

    try:
        client.loop_start()    #start mqtt loop to receive messages
        client.connect('10.0.0.10')
    except Exception as e:
        print('mqtt connection error: ' + str(e))
        return 0
        
    while not client.connected_flag and not client.bad_connection_flag: #wait in loop
        print("In wait loop")
        time.sleep(1)    

    if client.bad_connection_flag:
        print("mqtt connection error")
    if client.connected_flag:
        print("mqtt connection success")

    #response = open_port()  #open and close USB serial port
    time.sleep(2)
    #if not response:
    #    sys.exit()          #could not read USB serial port so exit the program
    
##    command = 'QID'         #get serial number from inverter
##    serial_number = serial_command(command)
##    if serial_number == 'USB Error':
##        sys.exit()          #exit program if serial number cannot be obtained
##    else:
##        print('Reading from inverter ' + serial_number)
##        #Reading from inverter '(92332004101045\x14\xb2   QID

    timer = 0
    timer2 = 0

    while True:
        time.sleep(1)
        timer += 1
        print('timer:' + str(timer))

        if timer == 30: #every 30 seconds query inverter for data
            print('timer:' + str(timer) + ' tripped')
            qpigs_data = 'qpigs'
            if qpigs_data == '':
                print('QPIGS no data')
                #sys.exit()
            else:
                print('qpigs_data='+qpigs_data)

            qmod_data = 'qmod'
            if qmod_data == '':
                print('QMOD no data')
                #sys.exit()
            else:
                print('qmod_data='+qmod_data)

            #   build json with all inverter data
            axpert_data = '{"SerialNumber":"' + str(timer) + '/' + str(timer2) + '","GridVoltage":249.0,"GridFrequency":49.8,"ACOutputVoltage":227.0,"ACOutputFrequency":49.8,"ACOutputApparentPower":166,"ACOutputActivePower":100,"OutputLoadPercent":6,"BusVoltage":476,"BatteryVoltage": 26.99,"BatteryChargingCurrent":0,"BatteryCapacity":100,"DeviceStatus":"10011101","Mode":"L"}'
            #print(axpert_data)

            send = send_data(axpert_data, 'power/axpert') #publish data to mqtt broker
            if send == 1:
                print("data published to mqtt broker")
            elif send == 0:
                print("error sending data to mqtt broker")

            #print("Publishing message to topic","power/axpert")
            #client.publish("power/axpert",'{"SerialNumber":"Test2","GridVoltage":249.0,"GridFrequency":49.8,"ACOutputVoltage":227.0,"ACOutputFrequency":49.8,"ACOutputApparentPower":166,"ACOutputActivePower":100,"OutputLoadPercent":6,"BusVoltage":476,"BatteryVoltage": 26.99,"BatteryChargingCurrent":0,"BatteryCapacity":100,"DeviceStatus":"10011101","Mode":"L"}', qos=2, retain=1)
            timer = 0
            timer2 += 1
            print('timer2:' + str(timer2))
            if timer2 == 20:
                print('timer2:' + str(timer2) + ' tripped')
                timer2 = 0
                client.loop_stop()    #stop mqtt loop to receive messages
                client.disconnect()
                break

#####################Test
##    qpigs_data = get_data_QPIGS()
##    if qpigs_data == '':
##        print('QPIGS no data')
##        #sys.exit()
##    else:
##        print('qpigs_data='+qpigs_data)
##
##    qmod_data = get_data_QMOD()
##    if qmod_data == '':
##        print('QMOD no data')
##        #sys.exit()
##    else:
##        print('qmod_data='+qmod_data)
##
##    #   build json with all inverter data
##    axpert_data = '{' + '"SerialNumber":"' + str(serial_number[1:]) + '",' + qpigs_data + "," + qmod_data + "}"
##    print(axpert_data)
##
##    send = send_data(axpert_data, os.environ['MQTT_TOPIC']) #publish data to mqtt broker
##    if send == 1:
##        print("data published to mqtt broker")
##    elif send == 0:
##        print("error sending data to mqtt broker")
##
##    time.sleep(10)
##
##    qpigs_data = get_data_QPIGS()
##    if qpigs_data == '':
##        print('QPIGS no data')
##        #sys.exit()
##    else:
##        print('qpigs_data='+qpigs_data)
##
##    qmod_data = get_data_QMOD()
##    if qmod_data == '':
##        print('QMOD no data')
##        #sys.exit()
##    else:
##        print('qmod_data='+qmod_data)
##
##    #   build json with all inverter data
##    axpert_data = '{' + '"SerialNumber":"' + str(serial_number[1:]) + '",' + qpigs_data + "," + qmod_data + "}"
##    print(axpert_data)
##
##    send = send_data(axpert_data, os.environ['MQTT_TOPIC']) #publish data to mqtt broker
##    if send == 1:
##        print("data published to mqtt broker")
##    elif send == 0:
##        print("error sending data to mqtt broker")
##
##    time.sleep(10)
##
##    qpigs_data = get_data_QPIGS()
##    if qpigs_data == '':
##        print('QPIGS no data')
##        #sys.exit()
##    else:
##        print('qpigs_data='+qpigs_data)
##
##    qmod_data = get_data_QMOD()
##    if qmod_data == '':
##        print('QMOD no data')
##        #sys.exit()
##    else:
##        print('qmod_data='+qmod_data)
##
##    #   build json with all inverter data
##    axpert_data = '{' + '"SerialNumber":"' + str(serial_number[1:]) + '",' + qpigs_data + "," + qmod_data + "}"
##    print(axpert_data)
##
##    send = send_data(axpert_data, os.environ['MQTT_TOPIC']) #publish data to mqtt broker
##    if send == 1:
##        print("data published to mqtt broker")
##    elif send == 0:
##        print("error sending data to mqtt broker")
##
#####################Test


    #time.sleep(5)
    #client.loop_stop() #stop the loop
    #client.disconnect() # disconnect from mqtt broker

############
if __name__ == '__main__':
    main()
