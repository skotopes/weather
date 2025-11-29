import math


def degToCompass(num):
    val = int((num / 22.5) + 0.5)
    arr = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    return arr[(val % 16)]


def luxToWatt(lux):
    return math.floor(lux * 0.0079 * 0.8)
