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
map_chars = None


def get_map(points, meta, data, download=True):
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
    return "/tmp/img.png"


def init():
    global d
    pygame.init()
    d = pygame.display.set_mode((650, 450))


def update_coords(clickx: int, clicky: int):
    global lon
    global lat
    half_wide = d.get_width()/2
    half_high = d.get_height()/2
    if clicky > half_high:
        lon -= 0.000005* abs(half_high-clicky) * (18-zoom)**3
    else:
        lon += 0.000005* abs(half_high-clicky) * (18-zoom)**3
    if clickx > half_wide:
        lat += 0.00001 * abs(half_wide-clickx) * (18-zoom)**3
    else:
        lat -= 0.00001* abs(half_wide-clickx) * (18-zoom)**3


def update_image():
    global map_chars
    if map_chars != ([], {'lang': 'ru_RU', 'width': d.get_width(), 'height': d.get_height(),
                          'type': 'map'}, {'z': zoom, 'll': '{},{}'.format(str(lat), str(lon))}):
        m = get_map([], {'lang': 'ru_RU', 'width': d.get_width(), 'height': d.get_height(),
                         'type': 'map'}, {'z': zoom, 'll': '{},{}'.format(str(lat), str(lon))})
        map_chars = ([], {'lang': 'ru_RU', 'width': d.get_width(), 'height': d.get_height(),
                          'type': 'map'}, {'z': zoom, 'll': '{},{}'.format(str(lat), str(lon))})
    i = pygame.image.load(get_map([], {}, {}, False))
    d.blit(i, (0, 0))
    pygame.draw.line(d, pygame.Color(['red', 'yellow', 'green'][kind - 1]), (0, d.get_height() // 2),
                     (d.get_width(), d.get_height() // 2), 3)
    pygame.draw.line(d, pygame.Color(['red', 'yellow', 'green'][kind - 1]), (d.get_width() // 2, 0),
                     (d.get_width() // 2, d.get_height()), 3)
    f=pygame.font.SysFont('BadFontMono', 32)
    lon_t=f.render('LON:{:.8}'.format(lon),False, pygame.Color('red'))
    lat_t=f.render('LAT:{:.8}'.format(lat),False, pygame.Color('red'))
    d.blit(lon_t, (d.get_width()/2, d.get_height()/2-32))
    d.blit(lat_t, (d.get_width()/2, d.get_height()/2))


    pygame.display.flip()


def loop():
    global zoom, kind
    update_image()
    while 1:
        d=False
        for i in pygame.event.get():
            if i.type == pygame.MOUSEBUTTONDOWN:
                if i.button == 1:
                    update_coords(i.pos[0], i.pos[1])
                    d = True
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
