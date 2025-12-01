import math
import aiohttp

from ecowitt_wn90lp.ws90 import WS90Client


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


async def getWeatherDataFromAPI(port):
    async with aiohttp.ClientSession() as session:
        async with session.get(port) as response:
            return await response.json()


async def getWeatherDataFromDevice(port):
    client = WS90Client(port)
    await client.connect()
    data = await client.read_all()
    client.close()

    return {
        "wind_direction": data.wind_direction,
        "gust_speed": data.gust_speed,
        "humidity": data.humidity,
        "light": data.light,
        "pressure_abs": data.pressure_abs,
        "rainfall": data.rainfall,
        "temperature": data.temperature,
        "uv_index": data.uv_index,
        "wind_direction": data.wind_direction,
        "wind_speed": data.wind_speed,
    }


async def getWeatherData(port):
    if port.startswith("http"):
        return await getWeatherDataFromAPI(port)
    else:
        return await getWeatherDataFromDevice(port)
