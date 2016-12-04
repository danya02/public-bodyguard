#!/usr/bin/python3
#    gps-tracker.py - Simple GPS tracking program
#    Copyright (C) 2016 Danya Generalov

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gpsd
import threading
import time
import gpiozero
import os
import signal
import paho.mqtt.client as mqtt
try:
    from ISStreamer.Streamer import Streamer
    IS = True
except:
    IS = False
ID = "DEADBEEF"
IPADDR = "127.0.0.1"
DEBUG = True
log = []


time.sleep(5)


def sync():
    global log
    logstr = ""
    for i in log:
        logstr += str(i[0]) + ":" + str(i[1]) + "\n"
    with open("/home/pi/log", "a") as logger:
        logger.write(logstr)
    log = []


def logroller():
    while 1:
        time.sleep(60)
        sync()


def debug(objs):
    global log
    if DEBUG:
        print("DEBUG:", objs)
        log += [(time.time(), objs)]

logroller_loop = threading.Thread(target=logroller)
logroller_loop.daemon = False
logroller_loop.start()


class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        for i in ["sats", "mode", "lat", "long",
                  "alt", "accx", "accy", "accz"]:
            self.__setattr__(i, 0)
        try:
            gpsd.connect()
        except:
            os.popen("sudo gpsd /dev/ttyUSB0")
            time.sleep(1)
            try:
                gpsd.connect()
            except:
                raise EnvironmentError("GPS server not available, " +
                                       "restart gpsd")

    def run(self):
        while 1:
            try:
                data = gpsd.get_current()
                self.sats = data.sats
                self.mode = data.mode
                if self.mode > 1:
                    self.lat = data.lat
                    self.long = data.lon
                    if self.mode > 2:
                        self.alt = data.alt
                self.accx = data.error["x"]  # values given in Minecraft format
                self.accy = data.error["v"]  # (X/Z axes horizontal,
                self.accz = data.error["y"]  # Y axis vertical)
                time.sleep(1)
            except IndexError:
                self.restart()

    def connect(self):
        gpsd.connect()

    def restart(self):
        os.popen("sudo service gpsd stop").read()
        os.popen("sudo service gpsd start").read()


def on_message(client, userdata, message):
    message = message.payload
    if "INTERVAL" in message:
        global interval
        interval = float(message.split(":")[1])
        debug("Interval set to "+str(interval))
    elif "SAFEMODE" in message:
        global update
        update = False if "ON" in message else True
        debug("Safe mode "+("exited" if update else "entered")+".")
    elif "LED" in message:
        global led
        led.value = True if "ON" in message else False
        debug("LED is now "+("on" if "ON" in message else "off")+".")
    elif "REBOOT" in message:
        debug("Rebooting system.")
        sync()
        os.system("sudo shutdown -r now")
    elif "TRACKBUT" in message:
        global trackbut
        trackbut = True if "ON" in message else False
        debug("Button tracking is now "+("on" if trackbut else "off")+".")
    elif "LOG" in message:
        debug("Logfile requested by remote.")
        sync()
        with open("/home/pi/log") as logread:
            logstr = logread.read()
        client.publish("status", payload=ID+":"+logstr, retain=False)
        debug("Logfile sent.")
    client.publish("status", payload=ID+":"+"ACK", retain=False)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        debug("Client connected to MQTT server.")
        global connected
        connected = True


def on_disconnect(client, userdata, rc):
    if rc:
        debug("Client disconnected from server.")
        global connected
        connected = False
        connect()


def connect():
    global connected
    global m
    attempt = 0
    while not connected:
        attempt += 1
        try:
            debug("Trying to connect to MQTT server," +
                  " attempt " + str(attempt) + ".")
            m = mqtt.Client()
            m.will_set("status", payload=ID+":DEAD", retain=True)
            m.subscribe("status")
            m.on_connect = on_connect
            m.on_message = on_message
            m.on_disconnect = on_disconnect
            m.connect(IPADDR)
            m.publish("status", payload=ID+":ALIVE", retain=True)
            m.loop_start()
        except:
            pass

global m
global connected
connected = False
connect()
global gpspoll
gpspoll = GpsPoller()
gpspoll.start()
global interval
interval = 1.0
global update
update = True
global trackbut
trackbut = True
global led
led = gpiozero.LED(2)
button = gpiozero.Button(21)


def send_button(button):
    global m
    global trackbut
    if trackbut:
        m.publish("status", payload=ID+":BUTTON"+":"+(
            "DOWN" if button.is_active else "UP"))
        debug("Button is "+("down." if button.is_active else "up."))
button.when_pressed = send_button
button.when_released = send_button


def sender_is():
    if IS:
        global gpspoll
        streamer = Streamer(bucket_name="GPS Tracker", bucket_key=ID,
                            access_key="00000000000000000000000000000000")
        while 1:
            time.sleep(5)
            streamer.log("Satellites", gpspoll.sats)
            if gpspoll.mode > 0:
                streamer.log("Location", "{lat},{long}".format(
                    lat=gpspoll.lat, long=gpspoll.long))
                streamer.log("Altitude", gpspoll.alt)
                streamer.log("Error", max(gpspoll.accx, gpspoll.accz))
                streamer.log("Error (vertical)", gpspoll.accy)
                debug("I told IS my location.")
            else:
                debug("I'm not telling IS my location.")


def sender_loc():
    global m
    global interval
    global update
    global gpspoll
    while 1:
        if update:
            try:
                assert(gpspoll.mode > 1)
                m.publish("status", payload=ID+":POS:"+str([gpspoll.lat,
                                                            gpspoll.long,
                                                            gpspoll.alt,
                                                            max(gpspoll.accx,
                                                                gpspoll.accz)]
                                                           ),
                          retain=True)
                debug("I am at "+str([gpspoll.lat, gpspoll.long, gpspoll.alt,
                                     max(gpspoll.accx, gpspoll.accz)]))
            except:
                m.publish("status", payload=ID+":POS:NOFIX", retain=True)
                debug("I don't have GPS fix.")
        time.sleep(interval)

sender_loop = threading.Thread(target=sender_loc)
sender_loop.daemon = True
sender_loop.start()
sender_loop_is = threading.Thread(target=sender_is)
sender_loop_is.daemon = True
sender_loop_is.start()
m.loop_start()
signal.pause()
