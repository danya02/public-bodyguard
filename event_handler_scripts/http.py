#!/usr/bin/python3
import urllib.request


class Requester:
    def __init__(self, url):
        self.url = url

    def __call__(self, lat=0, lon=0, alt=0, acc=0, level=0):
        urllib.request.urlopen(self.url.format(lat=lat, long=lon, alt=alt,
                                               acc=acc, level=level)).read()
