"""Retrieves a firmware file from Notehub given the firmware co-ordinates."""

import argparse
import base64
import hashlib
import json
import requests
import os
import notecard_firmware_query


def _assert_property(json, name):
    if not json.get(name):
        raise RuntimeError(f"no '{name}' property in {str(json)[0:500]}")
    return json[name]


def _get_notecard_firmware(filename, existing_md5=None) -> (dict, str):
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

    if existing_md5:
        # since the payload isn't retrieved, the MD5 given is for a zero-byte checksum, d41d8cd98f00b204e9800998ecf8427e
        # so we use the query API to get teh actual MD5
        selected = notecard_firmware_query.find_firmware(name=filename, allow=True)
        expected_md5 = _assert_property(selected, "md5")
        if existing_md5 == expected_md5:
            print("File already downloaded. Skipping download.")
            return selected, None   # return firmware info without payload
        else:
            print(f"Existing file MD5 differs: {existing_md5}!={expected_md5}")

    # now request with the length to get the firmware payload
    req_json = req_json | {"length": length}
    response = requests.get(url, headers=headers, json=req_json)

    if not response.ok:
        raise RuntimeError(
            f"Unable to retrieve Notecard firmware {filename}. {response.status_code}: {response.content}.")

    response_json: dict = response.json()
    body: dict = _assert_property(response_json, "body")
    md5 = _assert_property(response_json, "md5")
    payload = _assert_property(response_json, "payload")
    _assert_property(body, "length")
    # hub.upload.query and hub.upload.get return different shapes. Move stuff around to compensate
    del response_json["body"]
    del response_json["payload"]
    # move what remains from the root to the body so that it is the same as returned by hub.uploads.query
    for k in response_json.keys():
        body[k] = response_json[k]
    return body, payload


def _validate(firmware_json: dict, payload: str, existing_md5: str):
    md5 = firmware_json["md5"]
    length = firmware_json["length"]

    # no payload present, and the md5 doesn't match
    if not payload:
        if not existing_md5 or md5 != existing_md5:
            raise ValueError("payload expected but is not present")
        else:
            return None  # file already present and correct

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
    if payload_bytes:
        with open(filename, "wb") as binary_file:
            binary_file.write(payload_bytes)

    with open(f"{filename}.json", "wb") as json_file:
        json_file.write(json.dumps(firmware_json).encode("utf-8"))


def file_md5(filename: str) -> str:
    """Compute the MD5 of a file."""
    return hashlib.md5(open(filename, 'rb').read()).hexdigest() if os.path.isfile(filename) else None


def download_firmware(filename: str):
    """
    Download firmware from Notehub with the given filename.

    The same filename is used to write out the firmware file.
    The firmware json descriptor is written to a `.json` file.
    """
    existing_md5 = file_md5(filename)
    firmware_json, payload = _get_notecard_firmware(filename, existing_md5)
    payload_bytes = _validate(firmware_json, payload, existing_md5)
    _save(filename, firmware_json, payload_bytes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Retrieve available firmware from Notehub')

    parser.add_argument(
        "filename",
        help='The filename of the firmware to retrieve.')

    args = parser.parse_args()
    download_firmware(args.filename)
