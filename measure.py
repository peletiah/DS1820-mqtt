#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import logging
import re
import time

import paho.mqtt.client as mqtt

# MQTT configuration
MQTT_BROKER_IP = "10.0.0.30"
MQTT_BASE_TOPIC = "homeassistant/sensor/heizung/"
MQTT_BASE_ID = "heizung_temperatur_"
MQTT_NAME_PREFIX = "Heizung"
MQTT_RETAIN = True  # MQTT broker keeps the last message
MQTT_QOS = 2  # Make sure the MQTT message is only sent once

# Debugging

LOGLEVEL = logging.DEBUG
logging.basicConfig(level=LOGLEVEL)

SENSORS = [
    {
        "name": "Rücklauf Gesamt",
        "key": "ruecklauf_gesamt",
        "path": "/sys/bus/w1/devices/28-c6ad451f64ff/w1_slave",
    }
]

SENSOR_PARAMS = {
    "device_class": "temperature",
    "unit": "°C"
}


# function: read and parse sensor data file
def read_sensor(path):
    measurement = "0"
    try:
        f = open(path, "r")
        line = f.readline()
        if re.match(r"([0-9a-f]{2} ){9}: crc=[0-9a-f]{2} YES", line):
            line = f.readline()
            m = re.match(r"([0-9a-f]{2} ){9}t=([+-]?[0-9]+)", line)
            if m:
                measurement = str(float(m.group(2)) / 1000.0)
            f.close()
    except IOError as e:
        print(time.strftime("%x %X"), "Error reading", path, ": ", e)
    return measurement


def get_sensor_temps():
    # read values from all sensors
    sensor_temps = []
    for sensor in SENSORS:
        sensor['temperature'] = read_sensor(sensor['path'])
        sensor_temps.append(sensor)
    return sensor_temps


def mqtt_publish_config(mqtt_client):
    for sensor in SENSORS:
        name = sensor["name"]  # Entity name listed in HASS (Home Assistant) (e.g. "Temperature")
        device_class = SENSOR_PARAMS["device_class"]  # defines the icon used in HASS (e.g. "temperature")
        unit = SENSOR_PARAMS["unit"]  # defines the unit used in HASS (e.g. "°C")
        unique_id = f"{MQTT_BASE_ID}{sensor['key']}"  # unique identifier used in HASS (e.g. "tawes_temperature")
        value_template = f"{{{{ value_json.{unique_id}}}}}"  # defines how HASS extracts the value of this entity
        topic = f"{MQTT_BASE_TOPIC}{unique_id}/config"

        payload = {
            "device_class": device_class,
            "name": f"{MQTT_NAME_PREFIX} {name}",
            "state_topic": f"{MQTT_BASE_TOPIC}state",
            "unit_of_measurement": unit,
            "value_template": value_template,
            "unique_id": unique_id
        }

        logging.debug(f"config topic: {topic}")
        logging.debug(f"config payload: {payload}")
        mqtt_client.publish(topic, payload=json.dumps(payload), qos=MQTT_QOS, retain=MQTT_RETAIN)


def mqtt_publish_state(mqtt_client, sensor_data):
    topic = f"{MQTT_BASE_TOPIC}state"
    payload = dict()
    for sensor in sensor_data:
        payload[f"{MQTT_BASE_ID}{sensor['key']}"] = sensor["temperature"]

    logging.debug(f"state topic: {topic}")
    logging.debug(f"state payload: {payload}")
    mqtt_client.publish(topic, payload=json.dumps(payload), qos=MQTT_QOS, retain=MQTT_RETAIN)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag = True  # set flag
        logging.debug("connected OK")
    else:
        logging.debug("Bad connection Returned code=", rc)


def mqtt_run(sensor_temperatures):
    mqtt_client = mqtt.Client("DS1820")
    mqtt.Client.connected_flag = False
    logging.debug(f"Connecting to mqtt_broker_ip {MQTT_BROKER_IP}")

    mqtt_client.connect(MQTT_BROKER_IP)
    mqtt_client.on_connect = on_connect

    mqtt_client.loop_start()

    while not mqtt_client.connected_flag:
        logging.debug("In mqtt connect wait loop")
        time.sleep(1)
    logging.debug("Connected to mqtt broker")

    mqtt_publish_config(mqtt_client)
    mqtt_publish_state(mqtt_client, sensor_temperatures)

    mqtt_client.loop_stop()
    mqtt_client.disconnect()


if __name__ == "__main__":
    sensor_temperatures = get_sensor_temps()
    logging.debug(sensor_temperatures)
    mqtt_run(sensor_temperatures)
