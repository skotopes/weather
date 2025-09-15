#!/usr/bin/env python3

import os
import asyncio

from nicegui import app, ui, background_tasks
from ecowitt_wn90lp.ws90 import WS90Client
from datetime import datetime

import config

data = None


@ui.refreshable
def number_ui() -> None:
    if not data:
        ui.label("Waiting for data").classes("text-h1")
        return

    ui.label("Wind").classes("text-h3")
    with ui.circular_progress(10, min=0, max=360, show_value=False) as progress:
        progress.classes("size-72").props(f"angle={data.wind_direction-5} color='red'")
        wind_text = "?"
        if data.wind_speed > 0:
            wind_text = f"{data.wind_direction}˚"
        ui.label(wind_text).classes("text-h2")
    ui.markdown(
        f"Speed: {data.wind_speed}m/s<br>" f"Gust: {data.gust_speed}m/s<br>"
    ).classes("text-h4")

    ui.label("Other").classes("text-h3")
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
    with ui.element("div").classes("container mx-auto"):
        with ui.grid(columns=16).classes("w-full"):
            with ui.element().classes("col-span-12"):
                with ui.card():
                    ui.video(
                        "/video/stream.m3u8",
                        controls=True,
                        autoplay=True,
                        loop=True,
                    )
            with ui.element().classes("col-span-4"):
                with ui.card().classes("w-full"):
                    number_ui()


app.add_static_files("/video", "video")


async def backgroundRefreshData() -> None:
    global data

    client = WS90Client("/dev/cu.usbserial-110")
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
        config.VIDEO_STREAM_URL,
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


if config.VIDEO_STREAM_URL:
    app.on_startup(
        lambda: background_tasks.create_lazy(backgroundRunFFmpeg(), name="ffmpeg")
    )

ui.timer(1.0, backgroundRefreshData)

ui.run(title="Weather", dark=True)
