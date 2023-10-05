#!/usr/bin/python
# -*- coding: utf-8 -*-

import re, os, time

import json                                                                                                                                                                                                        
import logging
import time

import requests
import paho.mqtt.client as mqtt

# MQTT configuration
MQTT_BROKER_IP = "10.0.0.30"
MQTT_BASE_TOPIC = "homeassistant/sensor/heizung/"
MQTT_BASE_ID = "heizung_temperature"
MQTT_NAME_SUFFIX = "heizung"
MQTT_RETAIN = True  # MQTT broker keeps the last message
MQTT_QOS = 2  # Make sure the MQTT message is only sent once

# Debugging

LOGLEVEL = logging.DEBUG
logging.basicConfig(level=LOGLEVEL)

SENSOR_PARAMS = [
    {
        "name": "Heizung Rücklauf",
        "hass_key": "heizung_ruecklauf",
        "path":"/sys/bus/w1/devices/28-c6ad451f64ff/w1_slave",
    },
]


# function: read and parse sensor data file
def read_sensor(path):
    measurement = "U"
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


def get_sensor_data():
    # read values from all sensors
    sensor_data = [] 
    for sensor in SENSOR_PARAMS:
        sensor['temperature_value'] = read_sensor(sensor['path'])
        sensor['device_class'] = 'temperature'
        sensor_data.append(sensor)
    return sensor_data


def mqtt_publish_config(mqtt_client):
    for param in STATION_PARAMS.keys():
        if param in IGNORE_KEYS:
            continue

        name = STATION_PARAMS[param]["name"]  # Entity name listed in HASS (Home Assistant) (e.g. "Temperature")
        device_class = STATION_PARAMS[param]["device_class"]  # defines the icon used in HASS (e.g. "temperature")
        unit = STATION_PARAMS[param]["unit"]  # defines the unit used in HASS (e.g. "°C")
        unique_id = f"{MQTT_BASE_ID}{param}"  # unique identifier used in HASS (e.g. "tawes_temperature")
        value_template = f"{{{{ value_json.{unique_id}}}}}"  # defines how HASS extracts the value of this entity
        topic = f"{MQTT_BASE_TOPIC}{unique_id}/config"

        payload = {
            "device_class": device_class,
            "name": f"{name} {MQTT_NAME_SUFFIX}",
            "state_topic": f"{MQTT_BASE_TOPIC}state",
            "unit_of_measurement": unit,
            "value_template": value_template,
            "unique_id": unique_id
        }

        mqtt_client.publish(topic, payload=json.dumps(payload), qos=MQTT_QOS, retain=MQTT_RETAIN)


def mqtt_publish_state(mqtt_client, weather_data):
    topic = f"{MQTT_BASE_TOPIC}state"
    payload = dict()
    for key, value in weather_data.items():
        try:
            value = int(value)
        except ValueError:
            value = float(value.replace(",", "."))

        payload[f"{MQTT_BASE_ID}{key}"] = value

    mqtt_client.publish(topic, payload=json.dumps(payload), qos=MQTT_QOS, retain=MQTT_RETAIN)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag = True  # set flag
        logging.debug("connected OK")
    else:
        logging.debug("Bad connection Returned code=", rc)


def mqtt_run(station_weather):
    mqtt_client = mqtt.Client("tawes")
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
    mqtt_publish_state(mqtt_client, sensor_data)

    mqtt_client.loop_stop()
    mqtt_client.disconnect(

if __name__ == "__main__":
    sensor_data = get_sensor_data()
    logging.debug(sensor_data)
    mqtt_run(sensor_data)

