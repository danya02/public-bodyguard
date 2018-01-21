#!/usr/bin/python3

#    stationary-client.py - Simulation client for demo purposes
#    Copyright (C) 2018 Danya Generalov

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
import json
import urllib.request
import uuid

import pygame
import threading
import paho.mqtt.client as mqtt

d = None
m = None
lon = 55.75
lat = 37.62
kind = 3
zoom = 10
map = pygame.Surface((0, 0))
being_sent = False
blink_message = False
message = ''
message_color = pygame.Color(0, 0, 0, 0)
updates_left = 9001
map_chars = None


def get_map(points: list, meta: dict, data: dict, download=True):
    if not download:
        return '/tmp/img.png'
    addr = "http://static-maps.yandex.ru/1.x/?"
    addr += "l=" + str(meta["type"]) + "&size="
    addr += str(meta["width"]) + "," + str(meta["height"])
    addr += "&lang=" + str(meta["lang"]) + ("&pt=" if not points == [] else '')
    for i in data:
        addr += '&{}={}'.format(i, data[i])
    if not points == []:
        for i, j in zip(points, range(len(points) + 1)[1:]):
            addr += str(i["lat"]) + "," + str(i["long"]) + ","
            addr += str(i["style"]) + str(i["color"]) + str(i["size"])
            addr += str(i["content"])
            if not j == len(points):
                addr = addr + "~"
    with open(
            "/tmp/img.png", "wb") as o, urllib.request.urlopen(addr) as i:
        o.write(i.read())
    return pygame.image.load('/tmp/img.png')


def mqtt_on_connect(client: mqtt.Client, userdata, flags: dict, rc: int):
    global message, message_color, blink_message, updates_left
    if rc == 0:
        message = 'Connected to {}!'.format(client._host)
        message_color = pygame.Color(0, 255, 0, 255)
        blink_message = False
        updates_left = 25
    elif rc in [1, 2, 3, 4, 5]:
        message = 'Error connecting to {} - {}.'.format(client._host,
                                                        ['incorrect protocol version', 'invalid client identifier',
                                                         'server unavailable', 'bad username or password',
                                                         'not authorised'][rc])
        message_color = pygame.Color(255, 0, 0, 255)
        blink_message = True
        updates_left = 9001
    else:
        message = 'Unknown return code: {}'.format(rc)
        message_color = pygame.Color(0, 0, 0, 255)
        blink_message = False
        updates_left = 25


def mqtt_on_disconnect(client: mqtt.Client, userdata, rc: int):
    global message, message_color, blink_message, updates_left, being_sent
    being_sent = False
    message = 'Disconnected from {}! Reconnecting...'.format(client._host)
    message_color = pygame.Color(255, 0, 0, 255)
    blink_message = True
    updates_left = 9001


def mqtt_on_publish(client: mqtt.Client, userdata, mid: int):
    global message, message_color, blink_message, updates_left, being_sent
    being_sent = False
    message = 'SENT!'
    message_color = pygame.Color(0, 255, 0, 255)
    updates_left = 5
    blink_message = False


def mqtt_init():
    global m, message, message_color, blink_message, updates_left
    m = mqtt.Client()
    m.on_connect = mqtt_on_connect
    m.on_disconnect = mqtt_on_disconnect
    m.on_publish = mqtt_on_publish
    ip = '127.0.0.1'
    message = 'Connecting to {}...'.format(ip)
    message_color = pygame.Color(0, 0, 0, 255)
    blink_message = True
    updates_left = 9001
    mqtt_loop = threading.Thread(target=lambda: m.loop_forever(), name="MQTT thread", daemon=True)
    mqtt_loop.start()
    m.connect(ip)


def init():
    global d
    pygame.init()
    d = pygame.display.set_mode((650, 450))
    draw_loop = threading.Thread(target=redraw_image, name="Draw thread", daemon=True)
    draw_loop.start()
    mqtt_init()


def send_event(level: int, lat: float, lon: float):
    m.publish('/user/events', payload=json.dumps(
        {"uuid": '00000000-0000-0000-0000-000000000000', "euid": str(uuid.uuid1()), "level": level,
         "location": [lat, lon, 0, 0]}))


def update_coords(clickx: int, clicky: int):
    global lon
    global lat
    half_wide = d.get_width() / 2
    half_high = d.get_height() / 2
    if clicky > half_high:
        lon -= 0.000005 * abs(half_high - clicky) * (18 - zoom) ** 3
    else:
        lon += 0.000005 * abs(half_high - clicky) * (18 - zoom) ** 3
    if clickx > half_wide:
        lat += 0.00001 * abs(half_wide - clickx) * (18 - zoom) ** 3
    else:
        lat -= 0.00001 * abs(half_wide - clickx) * (18 - zoom) ** 3


def update_image():
    global map, map_chars, updates_left, message, message_color
    if map_chars != ([], {'lang': 'ru_RU', 'width': d.get_width(), 'height': d.get_height(),
                          'type': 'map'}, {'z': zoom, 'll': '{},{}'.format(str(lat), str(lon))}):
        map = get_map([], {'lang': 'ru_RU', 'width': d.get_width(), 'height': d.get_height(),
                           'type': 'map'}, {'z': zoom, 'll': '{},{}'.format(str(lat), str(lon))})
        map_chars = ([], {'lang': 'ru_RU', 'width': d.get_width(), 'height': d.get_height(),
                          'type': 'map'}, {'z': zoom, 'll': '{},{}'.format(str(lat), str(lon))})

    updates_left -= 1
    if updates_left <= 0:
        message = ''
        message_color = pygame.Color(0, 0, 0, 0)
        updates_left = 9001


def redraw_image():
    blink_phase = False
    blink_tick = 0
    f = pygame.font.SysFont('BadFontMono', 32)
    while 1:
        d.blit(map, (0, 0))
        pygame.draw.line(d, pygame.Color(['red', 'yellow', 'green'][kind - 1]), (0, d.get_height() // 2),
                         (d.get_width(), d.get_height() // 2), 3)
        pygame.draw.line(d, pygame.Color(['red', 'yellow', 'green'][kind - 1]), (d.get_width() // 2, 0),
                         (d.get_width() // 2, d.get_height()), 3)
        if being_sent:
            pygame.draw.line(d, pygame.Color(['red', 'yellow', 'green'][kind - 1]), (0, 0),
                             (d.get_width(), d.get_height()), 3)
            pygame.draw.line(d, pygame.Color(['red', 'yellow', 'green'][kind - 1]), (d.get_width(), 0),
                             (0, d.get_height()), 3)
        lon_t = f.render('LON:{:.8}'.format(lon), False, pygame.Color('red'))
        lat_t = f.render('LAT:{:.8}'.format(lat), False, pygame.Color('red'))
        message_t = f.render(message, False, message_color)
        d.blit(lon_t, (d.get_width() / 2, d.get_height() / 2 - 32))
        d.blit(lat_t, (d.get_width() / 2, d.get_height() / 2))
        if not blink_message:
            d.blit(message_t, (0, 0))
            blink_phase = False
            blink_tick = 0
        else:
            blink_tick += 1
            if blink_tick >= 2:
                blink_tick = 0
                blink_phase = not blink_phase
            if blink_phase:
                d.blit(message_t, (0, 0))
        pygame.time.delay(50)
        pygame.display.flip()


def loop():
    global zoom, kind, being_sent, message, message_color, updates_left, blink_message
    update_image()
    while 1:
        d = False
        for i in pygame.event.get():
            if not being_sent:
                if i.type == pygame.MOUSEBUTTONDOWN:
                    if i.button == 1:
                        update_coords(i.pos[0], i.pos[1])
                        d = True
                    elif i.button == 2:
                        being_sent = True
                        message = 'WAIT!'
                        message_color = pygame.Color(0, 0, 0, 255)
                        updates_left = 9001
                        blink_message = True
                        update_image()
                        send_event(kind, lat, lon)
                    elif i.button == 3:
                        kind += 1
                        if kind > 3:
                            kind = 1
                        d = True
                    elif i.button == 4:
                        zoom += 1
                        zoom = min(zoom, 17)
                        d = True
                    elif i.button == 5:
                        zoom -= 1
                        zoom = max(zoom, 0)
                        d = True

        pygame.time.delay(50)
        if d:
            update_image()


if __name__ == '__main__':
    init()
    loop()
