#!/usr/bin/python
#    server.py - MQTT request processor and addressor
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

import paho.mqtt.client as mqtt
import json
import time
import threading
import uuid
global to_cancel
to_cancel = []
conf = json.load(open("./config.json"))
global events
try:
    events = json.load(open(conf["path_to_event_list"]))["events"]
except:
    events = []
global log
try:
    log = json.load(open(conf["path_to_log"]))["log"]
except:
    log=[]
global messages
messages=0
m = mqtt.Client()
m.connect("127.0.0.1")
for i in ("data_chan", "event_chan", "reply_chan", "cancel_chan"):
    m.subscribe(conf[i])


def cancelmoose():
    global events
    global conf
    global to_cancel
    while 1:
        for i in events:
            if i["timestamp"]+conf["time_to_cancel"]["l"+str(i["level"])] < time.time():
                try:
                    to_cancel.remove(i)
                except:
                    pass
                if conf["debug"]:
                    print("Event of level "+i["level"]+" from user ID "+i["uuid"]+" with ID "+i["euid"]+" is canceled due to timeout")
                events.remove(i)
            if i in to_cancel:
                to_cancel.remove(i)
                if conf["debug"]:
                    print("Event of level "+i["level"]+" from user ID "+i["uuid"]+" with ID "+i["euid"]+" is canceled because of request")
                events.remove(i)
cancelmoose_thread=threading.Thread(target=cancelmoose, name="cancelmoose")
cancelmoose_thread.daemon=False
cancelmoose_thread.start()

def parser(client, userdata, msg):
    global log
    global messages
    global events
    global to_cancel
    messages+=1
    log=log+[{"topic":msg.topic, "payload":msg.payload}]
    if messages==conf["limit_to_save"]+1:
        messages=0
        json.dump({"log":log}, open(conf["path_to_log"],"w"))
        json.dump({"events":log}, open(conf["path_to_event_list"],"w"))
    if msg.topic==conf["data_chan"]:
        open(conf["path_to_data_folder"]+msg.payload.partition(
            "::")[0],"w").write(msg.payload.partition("::")[2])
    elif msg.topic==conf["event_chan"]:
        message=json.loads(msg.payload)
        message.update({"timestamp":time.time()})
        if conf["debug"]:
            print("Recieved event of level "+message["level"]+" from user ID "+message["uuid"]+", which was assigned ID "+message["euid"])
        events=events+[message]
    elif msg.topic==conf["cancel_chan"]:
        for i in events:
            if msg.payload.split("::")[0]==i["uuid"] and msg.payload.split("::")[1]==i["euid"]:
                to_cancel=to_cancel+[i]
m.on_message = parser
