import argparse
import requests


def list_notecard_firmware(allow, version):
    url = f'https://api.notefile.net/req'
    headers = {} # {'Authorization': f'Bearer {access_token}'}
    json = {"req": "hub.upload.query", "type": "notecard", "allow": allow, "version": version}

    response = requests.get(url, headers=headers, json=json)
    response_json = response.json()
    if not response.ok:
        raise RuntimeError(f"Unable to retrieve firmware list. {response.status_code}: {response.content}.")
    return response_json



def main(args):
    firmware = list_notecard_firmware(args.allow, args.version)
    print(firmware)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Retrieve available firmware from Notehub')

    parser.add_argument(
        '--target',
        required=False,
        default="",
        help='The target architecture.')

    parser.add_argument(
        '--version',
        required=False,
        help='The version to filter')

    parser.add_argument(
        '-a',
        '--allow',
        required=False,
        action='store_true',
        help='Allow use of non-release firmware.')

    args = parser.parse_args()

    main(args)
