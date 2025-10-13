#!/usr/bin/env python3

import os
import asyncio

from fastapi.responses import FileResponse

from nicegui import app, ui, background_tasks
from ecowitt_wn90lp.ws90 import WS90Client
from datetime import datetime
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

HEADER_BIG_SIZE = "text-h4"


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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DEBUG: bool = False
    VIDEO_STREAM_URL: str
    ECOWITT_WN90LP_PORT: str


settings = Settings()

data = None


@ui.refreshable
def number_ui() -> None:
    if not data:
        ui.label("Waiting for data").classes(HEADER_BIG_SIZE)
        return

    ui.label("Wind").classes(HEADER_BIG_SIZE)
    with ui.circular_progress(10, min=0, max=360, show_value=False) as progress:
        progress.classes("size-full").props(
            f"angle={data.wind_direction-5} color='red'"
        )
        wind_text = degToCompass(data.wind_direction)
        ui.label(wind_text).classes("text-h2")
    ui.markdown(
        f"Direction: {data.wind_direction}˚<br>"
        f"Speed: {data.wind_speed}m/s<br>"
        f"Gust: {data.gust_speed}m/s<br>"
    ).classes("text-h5")

    ui.label("Other").classes(HEADER_BIG_SIZE)
    ui.markdown(
        f"Light: {data.light} lux<br>"
        f"UV Index: {data.uv_index}<br>"
        f"Temperature: {data.temperature}˚C<br>"
        f"Humidity: {data.humidity}%<br>"
        f"Rainfall: {data.rainfall}<br>"
        f"Pressure: {data.pressure_abs/100} hPa"
    ).classes("text-h5")

    ui.label(f"Last Updated: {datetime.now().strftime('%a %d %b %Y, %H:%M:%S')}")


@ui.page("/")
def main_page() -> None:
    ui.add_head_html(
        '<link href="/static/video-js-8.21.1/video-js.min.css" rel="stylesheet">'
    )
    ui.add_head_html('<script src="/static/video-js-8.21.1/video.min.js"></script>')
    ui.add_head_html(
        "<style>.vjs-volume-panel, .q-loading-bar { display: none !important; }</style>"
    )

    with ui.element().classes("container mx-auto"):
        with ui.element().classes("row q-col-gutter-md"):
            with ui.element().classes("col-xs-12 col-lg-9"):
                with ui.card():
                    ui.label("Currently in the sky").classes(HEADER_BIG_SIZE)
                    with ui.element("video") as video:
                        video.classes("video-js vjs-default-skin w-full vjs-fluid")
                        video.props('autoplay controls preload="auto" data-setup="{}"')
                        ui.element("source").props('src="/video/stream.m3u8"')
            with ui.element().classes("col-xs-12 col-lg-3"):
                with ui.card().classes("w-full"):
                    number_ui()


@app.get("/video/stream.m3u8")
def generate_random_number():
    return FileResponse(
        "video/stream.m3u8",
        media_type="application/x-mpegurl",
        headers={"Cache-Control": "no-cache"},
    )


app.add_static_files("/video", "video")
app.add_static_files("/static", "static")


async def backgroundRefreshData() -> None:
    global data

    client = WS90Client(settings.ECOWITT_WN90LP_PORT)
    await client.connect()
    data = await client.read_all()
    client.close()
    number_ui.refresh()


async def backgroundRunFFmpeg() -> None:
    os.system("rm video/*")
    cmd = [
        "ffmpeg",
        "-nostats",
        "-loglevel",
        "error",
        "-i",
        settings.VIDEO_STREAM_URL,
        "-c:v",
        "copy",
        "-an",
        "-f",
        "hls",
        "-hls_time",
        "2",
        "-hls_list_size",
        "3",
        "-hls_segment_type",
        "mpegts",
        "-hls_flags",
        "delete_segments",
        "video/stream.m3u8",
    ]
    proc = None
    try:
        while True:
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
            await asyncio.sleep(1)
    finally:
        if proc:
            proc.kill()


app.on_startup(
    lambda: background_tasks.create_lazy(backgroundRunFFmpeg(), name="ffmpeg")
)

ui.timer(1.0, backgroundRefreshData)

ui.run(title="Weather", dark=True, reload=settings.DEBUG, show=settings.DEBUG)
