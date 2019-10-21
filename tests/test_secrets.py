#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_secrets.py
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

"""Tests for secrets.py."""

import base64
import os
import sys

try:
    import pytest
except ImportError:
    pass

# We add the upper dir to the path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
from isbg import secrets      # noqa: E402
from isbg import imaputils    # noqa: E402

# To check if a cmd exists:

def cmd_exists(x):
    """Check for a os command line."""
    return any(os.access(os.path.join(path, x), os.X_OK)
               for path in os.environ["PATH"].split(os.pathsep))


class Test_SecretIsbg(object):
    """Test SecretIsbg class."""

    def test_get_and_set(self):
        """Test the get and set functions."""
        imapset = imaputils.ImapSettings()

        # Test with a erroneous filename.
        sec = secrets.SecretIsbg(filename="", imapset=imapset)
        assert sec.get("foo") is None
        with pytest.raises(EnvironmentError, match=r"\[Errno "):
            sec.set("foo", "boo")
            pytest.fail("A EnvironmentError should be raised.")

        # Test with a ok filename:
        sec = secrets.SecretIsbg(filename="tmp.txt", imapset=imapset)
        assert sec.get("foo") is None
        sec.set("foo1", "boo1")
        sec.set("foo2", "boo2")
        sec.set("foo3", "boo3")
        sec.set("foo3", "boo4")
        assert sec.get("foo3") == "boo4"

        with pytest.raises(ValueError, match="Key 'foo3' exists."):
            sec.set("foo3", "boo5", overwrite=False)
            pytest.fail("It should raise a ValueError")

        assert sec.get("foo3") == "boo4"

        # Remove the created keys:
        sec.delete("foo1")
        assert sec.get("foo1") is None
        sec.delete("foo2")
        assert sec.get("foo2") is None

        # Remove non existant key:
        with pytest.raises(ValueError, match="Key 'foo4' not"):
            sec.delete("foo4")
            pytest.fail("It should raise a ValueError")

        # Remove last key, it should delete the file:
        sec.delete("foo3")
        assert sec.get("foo3") is None
        with pytest.raises(EnvironmentError, match=r"\[Errno 2\]"):
            os.remove("tmp.txt")
            pytest.fail("A EnvironmentError should be raised.")

        # Remove non existant key in non existant file:
        with pytest.raises(ValueError, match="Key 'foo4' not"):
            sec.delete("foo4")
            pytest.fail("It should raise a ValueError")
