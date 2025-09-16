# About

Weather station for Asagiri paragliding school.
Works with Ecowitt wn90lp sensor and external video camera.

# Requirements

- ffmpeg
- python 3
- poetry

# Configuring

Use environment variable or `.env` file to set configuration.

Options:

- `DEBUG` - run in debug mode with reloader and browser auto open
- `VIDEO_STREAM_URL` - video stream URL that will be passed to ffmpeg to convert into HLS format
- `ECOWITT_WN90LP_PORT` - serial port for Ecowitt wn90lp weather station RS485/Modbus interface

# Running

Run `poetry run ./app.py`
