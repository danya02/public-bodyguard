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

import urllib.request
import pygame
import time

d = None
lon = 55.75
lat = 37.62
kind = 3
zoom = 10


class MapGenerator:
    def __init__(self, pt, meta,data={}):
        if not isinstance(pt, list):
            raise TypeError("Expected <type 'list'>, got " + str(type(pt)) +
                            " instead")
        if not isinstance(meta, dict):
            raise TypeError("Expected <type 'dict'>, got " + str(type(meta)) +
                            " instead")
        self.points = pt
        self.meta = meta
        self.data = data

    def get_file(self):
        addr = "http://static-maps.yandex.ru/1.x/?"
        addr += "l=" + str(self.meta["type"]) + "&size="
        addr += str(self.meta["width"]) + "," + str(self.meta["height"])
        addr += "&lang=" + str(self.meta["lang"]) + ("&pt=" if not self.points == [] else '')
        for i in self.data:
            addr+='&{}={}'.format(i, self.data[i])
        if not self.points == []:
            for i, j in zip(self.points, range(len(self.points) + 1)[1:]):
                addr += str(i["lat"]) + "," + str(i["long"]) + ","
                addr += str(i["style"]) + str(i["color"]) + str(i["size"])
                addr += str(i["content"])
                if not j == len(self.points):
                    addr = addr + "~"
        with open(
                "/tmp/img.png", "wb") as o, urllib.request.urlopen(addr) as i:
            o.write(i.read())
        return "/tmp/img.png"

    def __str__(self):
        return self.get_file()


def init():
    global d
    pygame.init()
    d = pygame.display.set_mode((320, 240))


def update_coords(clickx, clicky):
    global lon
    global lat
    if clicky > d.get_height() / 2:
        lon -= 0.0001
    else:
        lon += 0.0001
    if clickx > d.get_width() / 2:
        lat += 0.0001
    else:
        lat -= 0.0001


def update_image():
    m = MapGenerator([], {'lang': 'ru_RU', 'width': d.get_width(), 'height': d.get_height(),
                          'type': 'map'}, {'z': zoom, 'll': '{},{}'.format(str(lat), str(lon))})
    i = pygame.image.load(m.get_file())
    del m
    d.blit(i, (0, 0))
    pygame.draw.line(d, pygame.Color(['red','yellow','green'][kind-1]), (0, d.get_height()//2), (d.get_width(), d.get_height()//2), 3)
    pygame.draw.line(d, pygame.Color(['red','yellow','green'][kind-1]), (d.get_width()//2,0), (d.get_width()//2, d.get_height()), 3)

    pygame.display.flip()


def loop():
    global zoom, kind
    update_image()
    while 1:
        for i in pygame.event.get():
            if i.type == pygame.MOUSEBUTTONDOWN:
                if i.button == 1:
                    update_coords(i.pos[0], i.pos[1])
                    update_image()
                elif i.button == 3:
                    kind+=1
                    if kind>3:
                        kind=1
                    update_image()
                elif i.button == 4:
                    zoom += 1
                    zoom = min(zoom, 17)
                    update_image()
                elif i.button == 5:
                    zoom -= 1
                    zoom = max(zoom, 0)
                    update_image()

        time.sleep(0.1)


if __name__ == '__main__':
    init()
    loop()
