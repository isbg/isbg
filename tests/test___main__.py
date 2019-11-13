#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_imaputils.py
#  This file is part of isbg.
#
#  Copyright 2018 Carles Muñoz Gorriz <carlesmu@internautas.org>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

"""Test cases for __main__ file."""

import os
import sys

try:
    import pytest
except ImportError:
    pass

from unittest import mock

# We add the upper dir to the path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
from isbg import __main__, isbg  # noqa: E402


def test_parse_args():
    """Test parse_args."""
    # Remove pytest options:
    orig_args = sys.argv[:]

    # Parse command line (it should work):
    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--flag",
               "--noninteractive"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    __main__.parse_args(sbg)
    assert sbg.imapsets.host == "localhost"
    assert sbg.imapsets.user == "anonymous"
    assert sbg.imapsets.passwd == "none"

    # Parse with unknown option
    del sys.argv[1:]
    for op in ["--foo"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    with pytest.raises(isbg.ISBGError, match="[options]"):
        __main__.parse_args(sbg)
        pytest.fail("It should rise a docopt SystemExit")

    # Parse with bogus deletehigherthan
    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--deletehigherthan",
               "0"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    with pytest.raises(isbg.ISBGError, match="too small"):
        __main__.parse_args(sbg)
        pytest.fail("It should rise a too small ISBGError")

    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--deletehigherthan",
               "foo"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    with pytest.raises(isbg.ISBGError, match="Unrecognized score"):
        __main__.parse_args(sbg)
        pytest.fail("It should rise a unrecognized score" + "ISBGError")

    # Parse with ok deletehigherthan
    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--deletehigherthan",
               "8"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    __main__.parse_args(sbg)
    assert sbg.deletehigherthan == 8.0

    # Parse with bogus maxsize
    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--maxsize", "0"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    with pytest.raises(isbg.ISBGError, match="too small"):
        __main__.parse_args(sbg)
        pytest.fail("It should rise a too small ISBGError")

    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--maxsize", "foo"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    with pytest.raises(isbg.ISBGError, match="Unrecognised size"):
        __main__.parse_args(sbg)
        pytest.fail("It should rise a Unrecognised size" + "ISBGError")

    # Parse with ok maxsize
    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--maxsize", "12000"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    __main__.parse_args(sbg)
    assert sbg.maxsize == 12000

    # Parse with bogus partialrun
    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--partialrun", "-10"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    with pytest.raises(isbg.ISBGError, match="equal to 0 or higher"):
        __main__.parse_args(sbg)
        pytest.fail("It should rise a equal to 0 or higher " + "ISBGError")

    # Parse with 0 partialrun
    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--partialrun", "0"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    __main__.parse_args(sbg)
    assert sbg.partialrun is None

    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--dryrun", "--partialrun", "foo"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    with pytest.raises(isbg.ISBGError, match="must be a integer"):
        __main__.parse_args(sbg)
        pytest.fail("It should rise a invalid literal " + "ValueError")

    # Parse with ok partialrun and verbose and nossl
    del sys.argv[1:]
    for op in ["--imaphost", "localhost", "--imapuser", "anonymous",
               "--imappasswd", "none", "--verbose", "--partialrun", "10",
               "--nossl"]:
        sys.argv.append(op)
    sbg = isbg.ISBG()
    __main__.parse_args(sbg)
    assert sbg.partialrun == 10

    # Restore pytest options:
    del sys.argv[1:]
    sys.argv = orig_args[:]


def test_main():
    """Test main()."""
    # Remove pytest options:
    args = sys.argv[:]
    del sys.argv[1:]
    sys.argv.append("--ignorelockfile")

    with mock.patch.object(isbg, "__name__", "__main__"):
        with pytest.raises(SystemExit, match="10"):
            __main__.main()
            pytest.fail("Not error or unexpected error")

    with pytest.raises(SystemExit, match="10"):
        with pytest.raises(isbg.ISBGError, match="10"):
            __main__.main()
            pytest.fail("Not error or unexpected error message")
        pytest.fail("Not error or unexpected error")

    sys.argv.append("--version")
    with mock.patch.object(isbg, "__name__", "__main__"):
        with pytest.raises(SystemExit):
            __main__.main()
            pytest.fail("Not error or unexpected error")

    sys.argv.append("--exitcodes")
    with mock.patch.object(isbg, "__name__", "__main__"):
        with pytest.raises(SystemExit):
            __main__.main()
            pytest.fail("Not error or unexpected error")

    del sys.argv[1:]
    sys.argv.append("--usage")
    with mock.patch.object(isbg, "__name__", "__main__"):
        with pytest.raises(SystemExit):
            __main__.main()
            pytest.fail("Not Exit or unexpected error")

    # Restore pytest options:
    sys.argv = args[:]
