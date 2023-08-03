import pytest
import notecard_dfu_util
import re

# Output captured from `dfu-util -l` with two Notecards connected via USB, both in bootloader mode
dfu_list_two_notecards = """
dfu-util 0.9

Copyright 2005-2009 Weston Schmidt, Harald Welte and OpenMoko Inc.
Copyright 2010-2016 Tormod Volden and Stefan Schmidt
This program is Free Software and has ABSOLUTELY NO WARRANTY
Please report bugs to http://sourceforge.net/p/dfu-util/tickets/

Found DFU: [0483:df11] ver=2200, devnum=5, cfg=1, intf=0, path="3-1", alt=2, name="@OTP Memory /0x1FFF7000/01*0001Ke", serial="205B3875594D"
Found DFU: [0483:df11] ver=2200, devnum=5, cfg=1, intf=0, path="3-1", alt=1, name="@Option Bytes  /0x1FF00000/01*040 e/0x1FF01000/01*040 e", serial="205B3875594D"
Found DFU: [0483:df11] ver=2200, devnum=5, cfg=1, intf=0, path="3-1", alt=0, name="@Internal Flash  /0x08000000/512*0004Kg", serial="205B3875594D"
Found DFU: [0483:df11] ver=2200, devnum=9, cfg=1, intf=0, path="4-1", alt=2, name="@OTP Memory /0x1FFF7000/01*0001Ke", serial="203C31685856"
Found DFU: [0483:df11] ver=2200, devnum=9, cfg=1, intf=0, path="4-1", alt=1, name="@Option Bytes  /0x1FF00000/01*040 e/0x1FF01000/01*040 e", serial="203C31685856"
Found DFU: [0483:df11] ver=2200, devnum=9, cfg=1, intf=0, path="4-1", alt=0, name="@Internal Flash  /0x08000000/512*0004Kg", serial="203C31685856"
"""


class TestDfuUtil:

    def test_finds_notecard_1(self):
        # this exercises the majority of the functionality for the happy path, apart from
        # launching dfu-util
        dfu_list = dfu_list_two_notecards
        filename = "abc#def.bin"
        serial = "203C31685856"
        devnum = 9
        cmd_args = notecard_dfu_util.build_dfu_util_command_args(
            dfu_list, serial, filename)

        self.assert_cmd_args(cmd_args, devnum, filename)

    def test_finds_notecard_2(self):
        # this exercises the majority of the functionality for the happy path, apart from
        # launching dfu-util
        dfu_list = dfu_list_two_notecards
        filename = "abc#def.bin"
        serial = "205B3875594D"
        devnum = 5
        cmd_args = notecard_dfu_util.build_dfu_util_command_args(
            dfu_list, serial, filename)

        self.assert_cmd_args(cmd_args, devnum, filename)

    def test_raises_exception_when_serial_does_not_match(self):
        # this exercises the majority of the functionality for the happy path, apart from
        # launching dfu-util
        dfu_list = dfu_list_two_notecards
        filename = "abc#def.bin"
        serial = "CANTFINDME"
        # errormsg is a Regex and has been escaped accordingly
        errormsg = "Cannot find a DFU region matching {'vid': '0483', 'pid': 'df11', 'name': '@Internal Flash  /0x08000000/512*0004Kg', 'serial': 'CANTFINDME'}"
        with pytest.raises(RuntimeError, match=re.escape(errormsg) + ".*"):
            notecard_dfu_util.build_dfu_util_command_args(
                dfu_list, serial, filename)

    def assert_cmd_args(self, cmd_args, devnum, filename):
        assert cmd_args[0] == "-n"
        assert cmd_args[1] == str(devnum)
        assert cmd_args[2] == "-a"
        assert cmd_args[3] == "0"
        assert cmd_args[4] == "-s"
        assert cmd_args[5] == "0x8000000:leave"
        assert cmd_args[6] == "-D"
        assert cmd_args[7] == filename
