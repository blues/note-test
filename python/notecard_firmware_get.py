"""Retrieves a firmware file from Notehub given the firmware co-ordinates."""

import argparse
import base64
import hashlib
import json
import requests


def _assert_property(json, name):
    if not json.get(name):
        raise RuntimeError(f"no '{name}' property in {str(json)[0:500]}")
    return json[name]


def _get_notecard_firmware(filename):
    url = 'https://api.notefile.net/req'
    headers = {}  # {'Authorization': f'Bearer {access_token}'}
    req_json = {"req": "hub.upload.get", "type": "notecard", "name": filename}
    response = requests.get(url, headers=headers, json=req_json)
    if not response.ok:
        raise RuntimeError(
            f"unable to query firmware matching name {filename}")

    response_json = response.json()
    body = response_json.get("body")
    if not body:
        raise RuntimeError(
            f"Notecard firmware not found matching name {filename}")

    _assert_property(body, "firmware")
    length = _assert_property(body, "length")
    if not length:
        raise RuntimeError(f"no length given for firmware {body}")

    # now request with the length to get the firmware payload
    req_json = req_json | {"length": length}
    response = requests.get(url, headers=headers, json=req_json)

    if not response.ok:
        raise RuntimeError(
            f"Unable to retrieve Notecard firmware {filename}. {response.status_code}: {response.content}.")

    response_json = response.json()
    body = _assert_property(response_json, "body")
    _assert_property(response_json, "md5")
    _assert_property(body, "length")
    _assert_property(response_json, "payload")

    return response_json


def _validate(firmware_json: dict):
    md5 = firmware_json["md5"]
    length = firmware_json["body"]["length"]
    payload = firmware_json["payload"]

    # decode base64
    base64_bytes = payload.encode("ascii")
    payload_bytes = base64.b64decode(base64_bytes)
    payload_length = len(payload_bytes)
    if length != payload_length:
        raise ValueError(
            f"payload length {payload_length} differs from expected {length}.")

    # check the md5
    actual_md5 = hashlib.md5(payload_bytes).hexdigest()
    if actual_md5 != md5:
        raise ValueError(
            f"payload MD5 {actual_md5} differs from expected {md5}.")
    return payload_bytes


def _save(filename: str, firmware_json, payload_bytes):
    with open(filename, "wb") as binary_file:
        binary_file.write(payload_bytes)

    del firmware_json["payload"]
    with open(f"{filename}.json", "wb") as json_file:
        json_file.write(json.dumps(firmware_json).encode("utf-8"))


def download_firmware(filename: str):
    """
    Download firmware from Notehub with the given filename.

    The same filename is used to write out the firmware file.
    The firmware json descriptor is written to a `.json` file.
    """
    firmware_json: dict = _get_notecard_firmware(filename)
    payload_bytes = _validate(firmware_json)
    _save(filename, firmware_json, payload_bytes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Retrieve available firmware from Notehub')

    parser.add_argument(
        "filename",
        help='The filename of the firmware to retrieve.')

    args = parser.parse_args()
    download_firmware(args.filename)
