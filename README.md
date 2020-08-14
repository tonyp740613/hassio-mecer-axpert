![inverters image](https://www.mecerpc.co.za/phpThumb/phpThumb.php?src=b64_aHR0cDovL3d3dy5jb214LmNvLnphL2kvbWVjZXIvc29sLWktYXgtM21wbHVzMjRfMS5qcGc=)
================

This is a Hassio addon to monitor Mecer Axpert inverters through USB and publish the data as JSON to an MQTT broker. It publishes the data to 1 topic:
- 'power/axpert' for the data from the connected inverter

You can then configure the sensors in Home Assistant like this:
```
sensors:
  - platform: mqtt
    name: "Power"
    state_topic: "power/axpert"
    unit_of_measurement: 'W'
    value_template: "{{ value_json.TotalAcOutputActivePower }}"
    expire_after: 60
```

The values published on 'power/axpert' are:
- Grid Voltage
- Grid Frequency
- AC Output Voltage
- AC Output Frequency
- AC Output Apparent Power
- AC Output Active Power
- Output Load Percent
- Bus Voltage
- Battery Voltage
- Battery Charging Current
- Battery Capacity
- Device Status
- Mode

I have a Mecer Axpert inverter SOL-I-AX-3M24 which is connected to a raspberry Pi 3 using the USB cable supplied with the inverter. In Linux the device is '/dev/hidraw0`.  
Using Python and paho-mqtt the inverter is queried for data using QPIGS and QMOD commands.  This data is parsed and then published using MQTT to Home Assistant.

