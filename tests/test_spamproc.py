#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_spamaproc.py
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

"""Tests for spamproc.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
try:
    import pytest
except ImportError:
    pass

from email.errors import MessageError

# We add the upper dir to the path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
from isbg import spamproc   # noqa: E402
from isbg import isbg       # noqa: E402
from isbg.imaputils import new_message  # noqa: E402

# To check if a cmd exists:


def cmd_exists(x):
    """Check for a os command line."""
    return any(os.access(os.path.join(path, x), os.X_OK)
               for path in os.environ["PATH"].split(os.pathsep))


def test_learn_mail():
    """Tests for learn_mail."""
    fmail = open('examples/spam.eml', 'rb')
    ftext = fmail.read()
    mail = new_message(ftext)
    fmail.close()

    if cmd_exists('spamc'):
        # We forget the mail:
        spamproc.learn_mail(mail, 'forget')
        # We forget the mail:
        ret, ret_o = spamproc.learn_mail(mail, 'forget')
        assert ret is 6, "Mail should be already unlearned."
        # We try to learn it (as spam):
        ret, ret_o = spamproc.learn_mail(mail, 'spam')
        assert ret is 5, "Mail should have been learned"
        # The second time it should be already learned:
        ret, ret_o = spamproc.learn_mail(mail, 'spam')
        assert ret is 6, "Mail should be already learned."
    else:
        # We forget the mail:
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.learn_mail(mail, 'forget')


def test_test_mail():
    """Tests for learn_mail."""
    fmail = open('examples/spam.eml', 'rb')
    ftext = fmail.read()
    mail = new_message(ftext)
    fmail.close()

    if cmd_exists('spamc'):
        # We test the mail with spamc:
        score1, code1 = spamproc.test_mail(mail, True)
        score2, code2 = spamproc.test_mail(mail, cmd=["spamc", "-c"])
        assert score1 == score2, "The score should be the same."
        assert code1 == code2, "The return code should be the same."
        score, code = spamproc.test_mail("", True)
        assert score == u'-9999', 'It should return a error'
        assert code is None, 'It should return a error'
    else:
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.test_mail(mail, True)
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.test_mail(mail, cmd=["spamc", "-c"])

    if cmd_exists('spamassassin'):
        # We test the mail with spamassassin:
        score3, code3 = spamproc.test_mail(mail, False)
        score4, code4 = spamproc.test_mail(mail, cmd=["spamassassin",
                                                      "--exit-code"])
        assert score3 == score4, "The score should be the same."
        assert code3 == code4, "The return code should be the same."
        score, code = spamproc.test_mail("", False)
        assert score == u'-9999', 'It should return a error'
        assert code is None, 'It should return a error'
    else:
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.test_mail(mail, False)
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.test_mail(mail, cmd=["spamassassin", "--exit-code"])

    # We try a random cmds (existant and unexistant):
    score, code = spamproc.test_mail("", cmd=["echo"])
    assert score == u'-9999', 'It should return a error'
    assert code is None, 'It should return a error'
    with pytest.raises(OSError, match="No such file",
                       message="Should rise OSError."):
        spamproc.test_mail(mail, cmd=["_____fooo___x_x"])


def test_feed_mail():
    """Test feed_mail."""
    fmail = open('examples/spam.eml', 'rb')
    ftext = fmail.read()
    mail = new_message(ftext)
    fmail.close()

    if cmd_exists('spamc'):
        # We test the mail with spamc:
        new_mail1, code1 = spamproc.feed_mail(mail, True)
        new_mail2, code2 = spamproc.feed_mail(mail, cmd=["spamc"])
        assert code1 == code2, "The return code should be the same."
        new_mail, code = spamproc.feed_mail("", True)
        assert new_mail == '-9999', 'It should return a error'
        assert code is None, 'It should return a error'
    else:
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.feed_mail(mail, True)
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.feed_mail(mail, cmd=["spamc"])

    if cmd_exists('spamassassin'):
        # We test the mail with spamassassin:
        new_mail3, code3 = spamproc.feed_mail(mail, False)
        new_mail4, code4 = spamproc.test_mail(mail, cmd=["spamassassin"])
        assert code3 == code4, "The return code should be the same."
        new_mail, code = spamproc.test_mail("", False)
        assert new_mail == u'-9999', 'It should return a error'
        assert code is None, 'It should return a error'
    else:
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.feed_mail(mail, False)
        with pytest.raises(OSError, match="No such file",
                           message="Should rise OSError."):
            spamproc.feed_mail(mail, cmd=["spamassassin"])

    # We try a random cmds (existant and unexistant
    new_mail, code = spamproc.feed_mail("", cmd=["echo"])
    assert new_mail == u'-9999', 'It should return a error'
    assert code is None, 'It should return a error'
    with pytest.raises(OSError, match="No such file",
                       message="Should rise OSError."):
        spamproc.feed_mail(mail, cmd=["_____fooo___x_x"])


class Test_Sa_Learn(object):
    """Tests for SA_Learn."""

    def test_sa_learn(self):
        """Test for sa_learn."""
        learn = spamproc.Sa_Learn()
        assert learn.tolearn == 0
        assert learn.learned == 0
        assert len(learn.uids) == 0
        assert len(learn.newpastuids) == 0


class Test_Sa_Process(object):
    """Tests for SA_Process."""

    def test_sa_process(self):
        """Test for sa_process."""
        proc = spamproc.Sa_Process()
        assert proc.nummsg == 0
        assert proc.numspam == 0
        assert proc.spamdeleted == 0
        assert len(proc.uids) == 0
        assert len(proc.newpastuids) == 0


class Test_SpamAssassin(object):
    """Tests for SpamAssassin."""

    _kwargs = ['imap', 'spamc', 'logger', 'partialrun', 'dryrun',
               'learnthendestroy', 'gmail', 'learnthenflag', 'learnunflagged',
               'learnflagged', 'deletehigherthan', 'imapsets', 'maxsize',
               'noreport', 'spamflags', 'delete', 'expunge']

    def test__kwars(self):
        """Test _kwargs is up to date."""
        assert self._kwargs == spamproc.SpamAssassin()._kwargs

    def test___init__(self):
        """Test __init__."""
        sa = spamproc.SpamAssassin()
        # All args spected has been initialized:
        for k in self._kwargs:
            assert k in dir(sa)

        sa = spamproc.SpamAssassin(imap=0)
        for k in self._kwargs:
            assert k in dir(sa)

        with pytest.raises(TypeError, match="Unknown keyword",
                           message="Should rise a error."):
            sa = spamproc.SpamAssassin(imap2=0)

    def test_cmd_save(self):
        """Test cmd_save."""
        sa = spamproc.SpamAssassin()
        assert sa.cmd_save == ['spamassassin']
        sa.spamc = True
        assert sa.cmd_save == ["spamc"]
        sa.spamc = False
        assert sa.cmd_save == ['spamassassin']

    def test_cmd_test(self):
        """Test cmd_test."""
        sa = spamproc.SpamAssassin()
        assert sa.cmd_test == ["spamassassin", "--exit-code"]
        sa.spamc = True
        assert sa.cmd_test == ["spamc", "-c"]
        sa.spamc = False
        assert sa.cmd_test == ["spamassassin", "--exit-code"]

    def test_create_from_isbg(self):
        """Test create_from_isbg."""
        sbg = isbg.ISBG()
        sa = spamproc.SpamAssassin.create_from_isbg(sbg)
        assert sa.imap is None  # pylint: disable=no-member
        assert sa.logger is not None

    def test_learn_checks(self):
        """Test learn checks."""
        sa = spamproc.SpamAssassin()
        with pytest.raises(isbg.ISBGError, match="Unknown learn_type",
                           message="Should rise error."):
            sa.learn('Spam', '', None, [])

        with pytest.raises(isbg.ISBGError, match="Imap is required",
                           message="Should rise error."):
            sa.learn('Spam', 'ham', None, [])

    def test_get_formated_uids(self):
        """Test get_formated_uids."""
        sbg = isbg.ISBG()
        sa = spamproc.SpamAssassin.create_from_isbg(sbg)

        # Test sorted and partialrun
        ret, oripast = sa.get_formated_uids(uids=[u'1 2 3'],
                                            origpastuids=[], partialrun=None)
        assert ret == [u'3', u'2', u'1']
        assert oripast == [], "List should be empty."

        ret, oripast = sa.get_formated_uids(uids=[u'1 2 3'],
                                            origpastuids=[], partialrun=3)
        assert ret == [u'3', u'2', u'1']
        assert oripast == [], "List should be empty."

        ret, oripast = sa.get_formated_uids(uids=[u'1 2 3'],
                                            origpastuids=[], partialrun=2)
        assert ret == [u'3', u'2']
        assert oripast == [], "List should be empty."

        # Test sorted and origpastuids. The uid '6' is not in the current uids,
        # and should be removed from the new origpastuids. And '3' should be
        # removed from the uids (it has been processed in the past).
        ret, oripast = sa.get_formated_uids(
            uids=[u'1 2 4 3'], origpastuids=[3, 1, 6], partialrun=2)
        print(oripast)
        print(ret)
        assert ret == [u'4', u'2']
        assert oripast == [3, 1], "Unexpected new orig past uids."

    def test_process_spam(self):
        """Test _process_spam."""
        sbg = isbg.ISBG()
        sa = spamproc.SpamAssassin.create_from_isbg(sbg)

        # OSError required when it's run without spamassassin (travis-cl)
        with pytest.raises((AttributeError, OSError, MessageError),
                           message="Should rise error, IMAP not created."):
            sa._process_spam(1, u"3/10\n", "", [])

        sa.noreport = True
        sa.deletehigherthan = 2
        sa._process_spam(1, u"3/10\n", "", [])

    def test_process_inbox(self):
        """Test process_inbox."""
        sbg = isbg.ISBG()
        sa = spamproc.SpamAssassin.create_from_isbg(sbg)
        with pytest.raises(AttributeError, match="has no attribute",
                           message="Should rise error, IMAP not created."):
            sa.process_inbox([])
