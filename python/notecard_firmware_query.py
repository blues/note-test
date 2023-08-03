"""
Query Notehub for firmware.

A Module exposing a function with a command-line front-end to find the name of Notecard firmware from Notehub corresponding to the firmware "co-ordinates" given.

Co-ordinates consist of:

* optional version
* optional target
* optional allow (for unpublished firmware)

The main function is find_firmware()
"""

import argparse
import functools
import json
import requests

notehub_default = "https://api.notefile.net"


def query_notecard_firmware(filename, notehub=notehub_default):
    """Query Notehub for a specific firmware, identified by name."""
    url = f'{notehub}/req'
    headers = {}  # {'Authorization': f'Bearer {access_token}'}
    req_json = {"req": "hub.upload.get", "allow": True,
                "type": "notecard", "name": filename}

    response = requests.get(url, headers=headers, json=req_json)
    response_json = response.json()
    if not response.ok:
        raise RuntimeError(
            f"Unable to retrieve firmware info for {filename}. {response.status_code}: {response.content}.")
    return response_json['body']


def list_notecard_firmware(allow: bool, notehub=notehub_default):
    """Query Notehub for all published firmware, and optionally unpublished firmware."""
    url = f'{notehub}/req'
    headers = {}  # {'Authorization': f'Bearer {access_token}'}
    req_json = {"req": "hub.upload.query", "type": "notecard", "allow": allow}

    response = requests.get(url, headers=headers, json=req_json)
    response_json = response.json()
    if not response.ok:
        raise RuntimeError(
            f"Unable to retrieve firmware list. {response.status_code}: {response.content}.")
    return response_json["uploads"]


def matches_version(fw: dict, required_components):
    """
    Determine if the version info in the firmware json matches the required version components.

    The components are assumed to be given as numbers in a list, in the order major, minor, patch and build.

    >>> matches_version({"ver_major":5, "ver_minor":4, "ver_patch":0, "ver_build":1234}, [5,4,0,1234])
    True
    """
    component_names = ["ver_major", "ver_minor", "ver_patch", "ver_build"]
    actual_components = [fw.get(name) for name in component_names]
    return matches_version_components(actual_components, required_components)


def matches_version_components(actual_components: list[int], required_components: list[int]) -> bool:
    """
    Determine if all the required version components match the actual version components.

    No requirements always matches
    >>> matches_version_components([], [])
    True
    >>> matches_version_components([5], [])
    True

    # Equal components match, as do components not required
    >>> matches_version_components([5], [5])
    True
    >>> matches_version_components([5,4], [5])
    True

    # Unequal components do not match, nor do missing actual components
    >>> matches_version_components([5,4], [5,3])
    False
    >>> matches_version_components([5,4], [5,4,3])
    False
    """
    matches = list(map(lambda i: i < len(actual_components) and required_components[i] == actual_components[i],
                       range(len(required_components))))
    result = functools.reduce(lambda x, y: x and y, matches, True)
    return result


def parse_version(version: str):
    """
    Parse a version string into a list of string components.

    >>> parse_version("5.6.7.1234")
    [5, 6, 7, 1234]
    """
    # todo - could use semver, but for now a simple split does the job
    return list(map(int, version.split('.') if version else []))


def _filter_firmware(firmware_list: list, version: str = None, target: str = None) -> list:
    required_version_components = parse_version(version)
    required_target = target or "r5"

    def predicate(fw: dict):
        # assume r5 target if none given
        firmware = fw["firmware"]
        target = firmware.get("target", "r5")
        return required_target == target and \
            matches_version(firmware, required_version_components)

    result = filter(predicate, firmware_list)
    return list(result)


def _comp_firmware(fw1, fw2):
    """
    Compare firmware json descriptors. Used for sorting.

    >>> _comp_firmware({"ver_major":5}, {"ver_major":5})
    0
    >>> _comp_firmware({"ver_major":5}, {"ver_major":6})
    -1
    >>> _comp_firmware({"ver_major":5, "ver_minor":4}, {"ver_major":5,"ver_minor":3})
    1
    >>> _comp_firmware({"ver_major":5, "ver_minor":6}, {"ver_major":5,"ver_minor":3, "ver_patch":7})
    3
    """

    def cmp_component(name):
        return fw1.get(name, 0) - fw2.get(name, 0)

    return cmp_component("ver_major") or \
        cmp_component("ver_minor") or \
        cmp_component("ver_patch") or \
        cmp_component("build") or 0


def sort_firmware(firmware: list):
    """Sorts the firmware by version."""

    def fw_order(f1, f2):
        return _comp_firmware(f1["firmware"], f2["firmware"])

    firmware.sort(reverse=True, key=functools.cmp_to_key(fw_order))
    return firmware


def find_firmware(name: str, allow: bool, as_json: bool = False, version: str = None, target: str = None):
    """
    Find firmware on Notehub that matches the given criteria.

    When as_json is false, the firmware name found is returned as a string. Otherwise the json
    firmware descriptor is returned, also as a string.
    """
    if name:
        selected = query_notecard_firmware(name)
    else:
        firmware = list_notecard_firmware(allow=allow)
        firmware = _filter_firmware(firmware, version, target)
        sort_firmware(firmware)
        if not len(firmware):
            raise ValueError("No firmware found.")

        selected = firmware[0]

    output = json.dumps(selected) if as_json else selected["name"]
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Query available firmware from Notehub.')

    parser.add_argument(
        '-n',
        '--name',
        help='The name of the firmware to retrieve.')

    parser.add_argument(
        '-t',
        '--target',
        required=False,
        default="r5",
        help='The target architecture.')

    parser.add_argument(
        '-v',
        '--version',
        required=False,
        default=None,
        help='''The version to retrieve, as [<major>[.<minor>[.<patch>[.build]]]].
                The highest version that matches will be returned if a 4 part version is not given. So, 5.4 would fetch the highest
                patch version, like 5.4.10.12345, but not version 5.5 or above.''')

    parser.add_argument(
        '-a',
        '--allow',
        required=False,
        action='store_true',
        default=False,
        help='Allow use of unpublished firmware.')

    parser.add_argument(
        '-j',
        '--json',
        required=False,
        action='store_true',
        default=False,
        help='Output detailed info of the firmware identified as json.')

    args = parser.parse_args()
    result = find_firmware(name=args.name,
                           allow=args.allow,
                           as_json=args.json,
                           target=args.target,
                           version=args.version)
    print(result, flush=True)
