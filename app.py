#!/usr/bin/env python3

import os
import logging
import asyncio

from datetime import datetime

from nicegui import app, ui, background_tasks
from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from helpers import *

HEADER_BIG_SIZE = "text-h4"

logger = logging.getLogger("weather")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DEBUG: bool = False
    VIDEO_STREAM_URL: str
    ECOWITT_WN90LP_PORT: str


settings = Settings()


class GlobalState:
    data = None
    ffmpeg_process = None


g = GlobalState()


@ui.refreshable
def number_ui() -> None:
    if not g.data:
        ui.label("Waiting for data").classes(HEADER_BIG_SIZE)
        return

    wind_text = degToCompass(g.data["wind_direction"])
    ui.label("Wind").classes(HEADER_BIG_SIZE)
    with ui.circular_progress(10, min=0, max=360, show_value=False) as progress:
        progress.classes("size-full").props(
            f"angle={g.data["wind_direction"]-5} color='red'"
        )
        ui.label(wind_text).classes("text-h2")
    ui.markdown(
        f"Direction: {g.data["wind_direction"]}˚ ({wind_text})<br>"
        f"Speed: {g.data["wind_speed"]}m/s<br>"
        f"Gust: {g.data["gust_speed"]}m/s<br>"
    ).classes("text-h5")

    ui.label("Other").classes(HEADER_BIG_SIZE)
    ui.markdown(
        f"Light: {g.data["light"]} lux ({luxToWatt(g.data["light"])} W)<br>"
        f"UV Index: {g.data["uv_index"]}<br>"
        f"Temperature: {g.data["temperature"]}˚C<br>"
        f"Humidity: {g.data["humidity"]}%<br>"
        f"Rainfall: {g.data["rainfall"]}<br>"
        f"Pressure: {g.data["pressure_abs"]/100} hPa"
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
    if not os.path.exists("video/stream.m3u8"):
        logger.error("Video stream is not ready")
        raise HTTPException(status_code=503, detail="Not ready")
    return FileResponse(
        "video/stream.m3u8",
        media_type="application/x-mpegurl",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/data")
def api_data():
    if not g.data:
        logger.error("Data stream is not ready")
        raise HTTPException(status_code=503, detail="Not ready")
    return JSONResponse(content=g.data)


app.add_static_files("/video", "video")
app.add_static_files("/static", "static")


async def backgroundRefreshData() -> None:
    global g

    # check latest data
    try:
        g.data = await getWeatherData(settings.ECOWITT_WN90LP_PORT)
        number_ui.refresh()
    except Exception as e:
        logger.exception(e)
        logger.error("Data update failed")

    # check video stream state
    try:
        if os.path.exists("video/stream.m3u8"):
            video_mtime = os.path.getmtime("video/stream.m3u8")
            now_mtime = datetime.now().timestamp()
            if now_mtime - video_mtime > 60 and g.ffmpeg_process:
                logger.error("Stale stream capture detected, killing ffmpeg")
                g.ffmpeg_process.kill()
    except Exception as e:
        logger.exception(e)
        logger.error("Video stream check failed")


app.timer(1.0, backgroundRefreshData)


async def backgroundRunFFmpeg() -> None:
    global g

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
        "10",
        "-hls_list_size",
        "6",
        "-hls_segment_type",
        "mpegts",
        "-hls_flags",
        "delete_segments",
        "video/stream.m3u8",
    ]

    try:
        while True:
            os.system("rm video/*")
            g.ffmpeg_process = await asyncio.create_subprocess_exec(*cmd)
            await g.ffmpeg_process.wait()
            await asyncio.sleep(1)
    except Exception as e:
        logger.exception(e)
    finally:
        if g.ffmpeg_process:
            g.ffmpeg_process.kill()


app.on_startup(
    lambda: background_tasks.create_lazy(backgroundRunFFmpeg(), name="ffmpeg")
)


ui.run(title="Weather", dark=True, reload=settings.DEBUG, show=settings.DEBUG)
