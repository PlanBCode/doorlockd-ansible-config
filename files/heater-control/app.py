#!/usr/bin/env python3
import glob
import argparse
import time
import logging
import gpiod
import atexit
import socket
import requests

import config

LOGGING_DEFAULT = "INFO"

logger = logging.getLogger(__name__)


def si7020_val(name):
    """Read value of si7020 sensor,  reading file by 'name' out of /sys/bus/i2c/drivers/si7020/*/iio:device*/."""
    try:
        path = glob.glob("/sys/bus/i2c/drivers/si7020/*/iio:device*/")[0]
    except IndexError:
        raise Exception(
            "No sensor found!, no data in '/sys/bus/i2c/drivers/si7020/*/iio:device*/'."
        )

    # return file contents of '/sys/bus/i2c/drivers/si7020/*/iio:device*/' + name
    return open(path + name).read()


def si7020_temp():
    return (
        (float(si7020_val("in_temp_raw")) + float(si7020_val("in_temp_offset")))
        * float(si7020_val("in_temp_scale"))
        / 1000
    )


def si7020_humid():
    return (
        (
            float(si7020_val("in_humidityrelative_raw"))
            + float(si7020_val("in_humidityrelative_offset"))
        )
        * float(si7020_val("in_humidityrelative_scale"))
        / 1000
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--show",
        action="store_true",
        help="Show temperature and relative humidity.",
    )
    parser.add_argument(
        "-d", "--deamon", action="store_true", help="start thermostaat deamon."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show log messages.",
    )
    parser.add_argument(
        "-l",
        "--log_level",
        default=LOGGING_DEFAULT,
        help="set loglevel for log messages. (CRITICAL/FATAL, ERROR, WARN/WARNING, INFO, DEBUG, NOTSET)",
    )
    args = parser.parse_args()

    # one of these or help:
    if args.show + args.deamon == 0:
        print("error: supply one task. see -h or --help")
        exit()

    elif args.show + args.deamon < 1:
        print("error: only supply one task. see -h or --help")
        exit()

    # enable logging:
    if args.verbose:
        if args.log_level.upper() not in logging.getLevelNamesMapping().keys():
            print(
                f"error: log-level not supported. must be one of: {', '.join(logging.getLevelNamesMapping().keys())}"
            )
            exit()

        logging.basicConfig(
            format=f"%(levelname)s:%(message)s \r",
            level=getattr(logging, args.log_level.upper()),
        )

    if args.show:
        print("settings:")
        for name, value in list(globals().items()):
            if name.isupper():
                print(name, "=", value)

        print(f"THRESHOLD_HUMID_ON = {config.THRESHOLD_HUMID_ON}")
        print(f"THRESHOLD_HUMID_OFF = {config.THRESHOLD_HUMID_OFF}")
        print(f"LOOP_WAIT = {config.LOOP_WAIT}")
        print("readings:")
        print("temp:  ", si7020_temp())
        print("humid: ", si7020_humid())

    if args.deamon:
        logger.info("starting thermostaat deamon")

        # Heater: gpio settings:
        gpio_chip, gpio_line = config.HEATER_GPIO

        # Heater: setup IO Chip + cleanup
        chip = gpiod.Chip(gpio_chip)
        atexit.register(chip.close)

        # Heater: setup IO Line as OUTPUT + cleanup
        pinconfig = {gpio_line: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)}
        io_lines = chip.request_lines(config=pinconfig)
        atexit.register(io_lines.release)

        #
        # run infinite loop
        #
        while True:
            humid = si7020_humid()
            temp = si7020_temp()
            timestamp_ns = time.time_ns()
            logger.debug(
                f"reading relative humidity = '{humid}', temperature = '{temp}"
            )

            # read heater state
            heater_state = bool(io_lines.get_value(int(gpio_line)))

            # heater_state is False or None |
            if heater_state != True and humid > THRESHOLD_HUMID_ON:
                # turn heater on
                io_lines.set_value(int(gpio_line), gpiod.line.Value.ACTIVE)
                logger.info(f"humidity above {config.THRESHOLD_HUMID_ON}, heater turned on.")

            # heater_state is True or None
            elif heater_state and humid < config.THRESHOLD_HUMID_OFF:
                # tunr heater off
                io_lines.set_value(int(gpio_line), gpiod.line.Value.INACTIVE)
                logger.info(
                    f"humidity below {config.THRESHOLD_HUMID_OFF}, heater turned off."
                )

            #
            # Send our data to influx
            #
            headers = {
                "Authorization": f"Token {config.INFLUX_TOKEN}",
                "Content-Type": "text/plain; charset=utf-8",
                "Accept": "application/json",
            }
            
            hostname = socket.gethostname()

            data = f"humidity,device=doorlock,location={config.INFLUX_LOCATION},device_id={hostname},host={hostname} humidity_RH={humid} {timestamp_ns}\n"
            data += f"temperature,device=doorlock,location={config.INFLUX_LOCATION},device_id={hostname},host={hostname} temperature_degC={temp} {timestamp_ns}\n"
            data += f"heater,device=doorlock,location={config.INFLUX_LOCATION},device_id={hostname},host={hostname} state={int(heater_state)} {timestamp_ns}\n"

            response = requests.post(
                config.INFLUX_URL, params=config.INFLUX_PARAMS, headers=headers, data=data
            )
            
            if not response.ok:
                logger.warning(f"influx failed: {response.text}")


            # end of loop
            time.sleep(config.LOOP_WAIT)

        logger.info("thermostaat deamon stopt.")
