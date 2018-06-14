#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_isbg.py
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

"""Test cases for isbg module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# With atexit._run_exitfuncs()  we free the lockfile, but we lost coverage
# statistics.

import os
import sys
try:
    import pytest
except ImportError:
    pass

# We add the upper dir to the path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
from isbg import isbg  # noqa: E402


def test_ISBGError():
    """Test a ISBGError object creation."""
    with pytest.raises(isbg.ISBGError, match="foo"):
        raise isbg.ISBGError(0, "foo")


class TestISBG(object):
    """Tests for class ISBG."""

    def test_set_filename(self):
        """Test set_filename."""
        sbg = isbg.ISBG()
        filename = isbg.ISBG.set_filename(sbg.imapsets, "track")
        assert os.path.dirname(filename) != ""
        assert os.path.basename(filename) != ""
        assert os.path.basename(filename).startswith("track")
        filename = isbg.ISBG.set_filename(sbg.imapsets, "password")
        assert os.path.dirname(filename) != ""
        assert os.path.basename(filename) != ""
        assert os.path.basename(filename).startswith(".isbg-")

    def test_removelock(self):
        """Test removelock."""
        sbg = isbg.ISBG()
        sbg.removelock()
        assert os.path.exists(sbg.lockfilename) is False, \
            "File should not exist."
        lockfile = open(sbg.lockfilename, 'w')
        lockfile.write(repr(os.getpid()))
        lockfile.close()
        assert os.path.exists(sbg.lockfilename), "File should exist."
        sbg.removelock()
        assert os.path.exists(sbg.lockfilename) is False, \
            "File should not exist."

    def test_do_isbg(self):
        """Test do_isbg."""
        sbg = isbg.ISBG()
        with pytest.raises(isbg.ISBGError, match="specify your imap password",
                           message=("It should rise a specify imap password " +
                                    "ISBGError")):
            sbg.do_isbg()
