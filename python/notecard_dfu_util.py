"""
A module to perform Notecard firmware updates using `dfu-util.

The device to receive the firmware is identified by its unique hardware id,
also known as the serial number.
"""

import argparse
import subprocess

_found_dfu = "Found DFU: "


def is_dfu_line(line: str) -> bool:
    """
    Determine if a string contains DFU interface information.

    >>> is_dfu_line("abc")
    False
    >>> is_dfu_line(_found_dfu)
    True
    """
    return line.startswith(_found_dfu)


def parse_dfu_line(line: str) -> dict:
    """
    Parse a dfu line into a dict, stripping quotes from quoted values..

    >>> parse_dfu_line('Found DFU: [abcd:1234] a=1, b="abc"')
    {'a': '1', 'b': 'abc', 'vid': 'abcd', 'pid': '1234'}
    >>> parse_dfu_line('Found DFU: [0483:df11] ver=2200, devnum=5, cfg=1, intf=0, path="3-1", alt=2, name="@OTP Memory /0x1FFF7000/01*0001Ke", serial="205B3875594D"')
    {'ver': '2200', 'devnum': '5', 'cfg': '1', 'intf': '0', 'path': '3-1', 'alt': '2', 'name': '@OTP Memory /0x1FFF7000/01*0001Ke', 'serial': '205B3875594D', 'vid': '0483', 'pid': 'df11'}
    """
    assert line.startswith("Found DFU: ")
    line = line[len(_found_dfu):]

    assert line[0] == '['
    assert line[5] == ':'
    assert line[10] == ']'
    vid = line[1:5]
    pid = line[6:10]
    # make the formatting more regular for vid/pid
    line = line[11:] + f", vid={vid}, pid={pid}"

    return {k.strip(): v.strip('"') for [k, v] in (item.split("=") for item in line.split(", "))}


def parse_dfu_output(lines: list[str]) -> list[dict]:
    """
    Parse a number of lines, looking for DFU details.

    >>> parse_dfu_output(["Not a DFU line","Found DFU: [1234:5678] ser=ABCDEF","Ignore this"])
    [{'ser': 'ABCDEF', 'vid': '1234', 'pid': '5678'}]
    """
    return [parse_dfu_line(line) for line in lines if is_dfu_line(line)]


def is_match(needle: dict, haystack: dict) -> bool:
    """
    Determine if haystack contains all the dictionary keys and values in needle.

    >>> is_match({'a':1}, {'a':2})
    False
    >>> is_match({'a':1}, {'b':1})
    False
    >>> is_match({}, {'b':1})
    True
    >>> is_match({'a':1, 'b':"abc"}, {'b':"abc","a":1, "c":0})
    True
    """
    return needle.items() <= haystack.items()


def _find_one_matching(needle: dict, haystack: list[dict]):
    found = [item for item in haystack if is_match(needle, item)]
    match len(found):
        case 0:
            return None
        case 1:
            return found[0]
        case _:
            raise ValueError(f"{needle} found more than once in {haystack}")


def run_command(cmd: str, cmd_args: list[str], timeout: float = None, capture_output: bool = True):
    """Execute an external program with given arguments and a timeout, with optional output stream capture."""
    args_list = [cmd] + cmd_args
    print(f"Running {' '.join(args_list)}")
    try:
        result = subprocess.run(args_list, encoding="utf-8",
                                capture_output=capture_output, timeout=timeout, check=True)
        return result.stdout
    except Exception as e:
        raise RuntimeError(f"command {args_list} failed") from e


notecard_r5_dfu_id = {
    "vid": "0483",
    "pid": "df11",
    "name": "@Internal Flash  /0x08000000/512*0004Kg"
}

notecard_dfu_address = "0x8000000"
dfu_util_cmd = "dfu-util"


def build_dfu_util_command_args(dfu_list: str, serial_number: str, filename: str) -> list[str]:
    """Build the command arguments to dfu-util based on the output from `dfu-util -l.`."""
    lines = dfu_list.splitlines()
    dfu_regions = parse_dfu_output(lines)
    find = notecard_r5_dfu_id | {"serial": serial_number}
    found = _find_one_matching(find, dfu_regions)

    try:
        if not found:
            raise RuntimeError(
                f"Cannot find a DFU region matching {find} in {dfu_regions}.")
    except Exception as e:
        print(lines, flush=True)
        raise e

    devnum = found.get("devnum")
    alt = found.get("alt")
    addr = notecard_dfu_address

    cmd_args = [
        "-n", f"{devnum}",
        "-a", f"{alt}",
        # leave instructs the bootloader to exit when done
        "-s", f"{addr}:leave",
        "-D", f"{filename}"
    ]
    return cmd_args


def dfu_util(filename: str, serial_number: str, timeout: float):
    """Perform a DFU against a notecard with the given serial number."""
    dfu_list = run_command(
        dfu_util_cmd, ["-l"], capture_output=True, timeout=20)
    dfu_args = build_dfu_util_command_args(dfu_list, serial_number, filename)

    # Now do the transfer, sending output to stdout
    run_command(dfu_util_cmd, dfu_args, capture_output=False, timeout=timeout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Updates Notecard firmware using dfu-util')

    # parser.add_argument(
    #     '--no-reset',
    #     required=False,
    #     default=False,
    #     action="store_true",
    #     help="Do not reset the device after the DFU completes."
    # )

    parser.add_argument(
        '-t',
        '--timeout',
        required=False,
        default=60 * 5,
        help='How long, in seconds, to wait for the DFU to finish.')

    parser.add_argument(
        '--serial-number',
        required=True,
        help='The serial number of the device to flash.')

    parser.add_argument(
        'filename',
        help='The name of the local file to transfer.')

    args = parser.parse_args()
    dfu_util(**vars(args))
