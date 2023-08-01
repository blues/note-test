## Updates Notecard firmware using a local serial connection to the Notecard.
import argparse
import notecard
from notecard import Notecard, start_timeout, has_timed_out
import serial
import time
import json


start = time.time()
def log(s: str):
    ts = time.time()-start
    print(f"{ts}: {s}", flush=True)

def try_transaction(card: Notecard, req: dict):
    result: dict = card.Transaction(req)
    if result.get("err"):
        raise RuntimeError(result)
    return result


def update_notecard_firmware(card: Notecard, filename: str, version: str, timeout: int):

    # check current version
    if version:
        card_version = try_transaction(card, {"req":"card.version"})
        log(f"current version: {card_version['version']}")
        if version==card_version["version"]:
            log(f"Skipping update. Notecard firmware at version requested: {version}.")
            return

    # stop any current DFU operation
    stop_dfu = {"req": "dfu.status", "name": "card", "off":True}
    try_transaction(card, stop_dfu)

    sync = {"req":"hub.sync", "allow": True}
    try_transaction(card, sync)

    # set the environment variables to start a new DFU
    now = int(time.time())
    try:
        try_transaction(card, {"req":"env.set", "name":"_fwc", "text":filename})
        try_transaction(card, {"req":"env.set", "name":"_fwc_retry", "text":str(now)})

        start_dfu = {"req":"dfu.status", "on":True, "name": "card"}
        try_transaction(card, start_dfu)

        try_transaction(card, sync)

        start_time = start_timeout()
        # wait for the DFU to begin - it can take a few seconds for a previously complete
        # DFU to change status, which is why we wait for it to change from completed.
        wait_for_dfu_mode(card, lambda mode: mode!="completed" and mode!="error",
                          start_time=start_time, timeout_secs=timeout, check_error=False)
        wait_for_dfu_mode(card, lambda mode: mode=="completed",
                          start_time=start_time, timeout_secs=timeout)
        log("DFU update complete.")

        card_version = try_transaction(card, {"req":"card.version"})
        actual_version = card_version["version"]
        log(f"current version: {actual_version}")
        if version != actual_version:
            raise RuntimeError(f"DFU update complete, version mismatch. Expected: {version}, actual: {actual_version}")
    finally:
        try_transaction(card, {"req":"env.set", "name":"_fwc"})
        try_transaction(card, {"req":"env.set", "name":"_fwc_retry"})
        try_transaction(card, sync)


def wait_for_dfu_mode(card, mode_predicate, poll_interval_secs=5, status_timeout=5*60, start_time=None, timeout_secs=30*60, check_error=True):
    if not start_time:
        start_time = start_timeout()
    status_start_time = start_timeout()
    req_dfu_status =  {"req":"dfu.status",  "name": "card"}
    dfu_status: dict = try_transaction(card, req_dfu_status)
    last_status: dict = dfu_status
    log(f"dfu status: {dfu_status}")

    while not mode_predicate(dfu_status["mode"]) and check_timed_out(start_time, timeout_secs, "DFU timeout") and check_timed_out(status_start_time, status_timeout, "DFU status timeout"):
        if last_status != dfu_status:
            status_start_time = start_timeout()
            log(f"dfu status: {dfu_status}")
        last_status = dfu_status
        if last_status["mode"] == "error" and check_error:
            raise RuntimeError(f"DFU update failed. {dfu_status}")
        time.sleep(poll_interval_secs)
        dfu_status = try_transaction(card, req_dfu_status)


def check_timed_out(start_time, timeout_secs, message="Timeout"):
    if has_timed_out(start_time, timeout_secs):
        raise TimeoutError(f"DFU update timeout. {message}")
    return True

def open_notecard(args):
    # todo - add I2C
    card = None
    start_time = start_timeout()
    timeout = args.card_timeout
    count = 0
    last_error = None
    while not card and check_timed_out(start_time, timeout, "open Notecard"):
        if count > 0:
            time.sleep(10)
        try:
            port = serial.Serial(port=args.serial_port, baudrate=args.baudrate)
            card = notecard.OpenSerial(port)
        except Exception as e:
            last_error = e
        count += 1
    if last_error:
        raise last_error
    return card


def main(args):
    # the serial port is closed if it's a USB connection, when the Notecard restarts after
    # applying the firmware. So retries should be at least 2
    retries = args.retries
    last_error = None
    success = False
    while not success and retries:
        try:
            retries -= 1
            log("Opening Notecard...")
            card = open_notecard(args)
            log(f"Updating firmware: {args}")
            update_notecard_firmware(card, args.filename, args.version, args.timeout)
            success = True
        except Exception as e:
            last_error = e
            time.sleep(20)  # sleep to give the Notecard time to restart
    if last_error:
        raise last_error
    log("Success. Exiting.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Update local Notecard firmware via Notehub')

    parser.add_argument(
        '-p',
        '--serial-port',
        required=True,
        help='The serial port the Notecard is available on.')

    parser.add_argument(
        '-b',
        '--baudrate',
        default=9600,
        required=False,
        help='The baudrate of the serial port.')

    parser.add_argument(
        '-f',
        '--filename',
        required=True,
        help='The filename in Notehub of the firmware to install.')

    parser.add_argument(
        '-v',
        '--version',
        required=True,
        help='The version string returned by card.status when the firmware has been updated.')

    parser.add_argument(
        '-r',
        '--retries',
        required=False,
        default=3,
        help='How many times the DFU is retried on error.')

    parser.add_argument('-c',
        '--card-timeout',
        required=False,
        default=30,
        help='How long, in seconds, to wait for the Notecard to become available.')

    parser.add_argument('-t',
        '--timeout',
        required=False,
        default=30*60,
        help='How long to wait, in seconds, before giving up on the DFU.')

    args = parser.parse_args()

    main(args)
