#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  spamaproc.py
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

"""Spam processing module for isbg."""
# pylint: disable=no-member

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import isbg

from isbg import imaputils
from isbg import sa_unwrap
from isbg import utils

from .utils import __

import logging

#: Used to detect already our successfully (un)learned messages.
__spamc_msg__ = {
    'already': 'Message was already un/learned',
    'success': 'Message successfully un/learned'
}


def learn_mail(mail, learn_type):
    """Process a email and try to learn or unlearn it.

    Args:
        mail (email.message.Message): email to learn.
        learn_type (str): ```spam``` to learn spam, ```ham``` to learn
            nonspam or ```forget```.
    Returns:
        int, int: It returns a pair of `int`

        The first integer:
            A return code of ``6`` means it was already learned or forgotten,
            a return code of ``5`` means it has been learned or forgotten,
            a ``-9999`` means an error communicating with ``spamc``. If
            ``spamc`` returns an exit code, it returns it.

        The second integer:
            It's the original exit code from ``spamc``

    Notes:
        See `Exit Codes` section of the man page of ``spamc`` for more
        information about other exit codes.

    """
    out = ""
    orig_code = None
    proc = utils.popen(["spamc", "--learntype=" + learn_type])
    try:
        out = proc.communicate(imaputils.mail_content(mail))
        code = int(proc.returncode)
        orig_code = code
    except Exception:  # pylint: disable=broad-except
        code = -9999

    proc.stdin.close()

    if code == 0:
        out = out[0].decode(errors='ignore').strip()
        if out == __spamc_msg__['already']:
            code = 6
        elif out == __spamc_msg__['success']:
            code = 5

    return code, orig_code


def test_mail(mail, spamc=False, cmd=False):
    """Test a email with spamassassin."""
    score = "0/0\n"
    orig_code = None

    cmd_score = ["spamassassin", "--exit-code"]
    if cmd:
        satest = cmd
    elif spamc:
        satest = ["spamc", "-c"]
    else:
        satest = ["spamassassin", "--exit-code"]

    proc = utils.popen(satest)
    try:
        score = proc.communicate(imaputils.mail_content(mail)
                                 )[0].decode(errors='ignore')
        if cmd_score == satest:
            score = utils.score_from_mail(score)
        orig_code = proc.returncode

    except Exception:  # pylint: disable=broad-except
        score = "-9999"

    proc.stdin.close()

    return score, orig_code


def feed_mail(mail, spamc=False, cmd=False):
    """Feed a email with spamassassin report."""
    new_mail = ""
    orig_code = None

    if cmd:
        sasave = cmd
    elif spamc:
        sasave = ["spamc"]
    else:
        sasave = ["spamassassin"]

    proc = utils.popen(sasave)
    try:
        new_mail = proc.communicate(imaputils.mail_content(mail))[0]
        orig_code = proc.returncode
    except Exception:  # pylint: disable=broad-except
        new_mail = u"-9999"

    proc.stdin.close()

    return new_mail, orig_code


class Sa_Learn(object):
    """Commodity class to store information about learning processes."""

    def __init__(self):
        """Initialize `SA_Learn`."""
        self.tolearn = 0         #: Number of messages to learn.
        self.learned = 0         #: Number of messages learned.
        self.uids = []           #: The list of ``uids``.
        self.newpastuids = []    #: The new past ``uids``.


class Sa_Process(object):
    """Commodity class to store information about processes."""

    def __init__(self):
        """Initialize `SA_Process`."""
        self.nummsg = 0          #: Number of processed messages.
        self.numspam = 0         #: Number of spams found.
        self.spamdeleted = 0     #: Number of deleted spam.
        self.uids = []           #: The list of ``uids``.
        self.newpastuids = []    #: The new past ``uids``.


class SpamAssassin(object):
    """Learn and process spams from a imap account.

    You usually will create an instance of it using
    :py:func:`create_from_isbg`:

        >>> sa = isbg.spamproc.SpamAssassin.create_from_isbg(self)

    Or, if you are extending :py:class:`~isbg.ISBG`, it is created every
    time that you call to :py:func:`isbg.ISBG.do_spamassassin`.

    """

    #: key args required when initialized.
    _required_kwargs = []

    #: Key args that will be used.
    _kwargs = ['imap', 'spamc', 'logger', 'partialrun', 'dryrun',
               'learnthendestroy', 'gmail', 'learnthenflag', 'learnunflagged',
               'learnflagged', 'deletehigherthan', 'imapsets', 'maxsize',
               'noreport', 'spamflags', 'delete', 'expunge']

    def __init__(self, **kwargs):
        """Initialize a SpamAssassin object."""
        for k in self._required_kwargs:
            if k not in kwargs:
                raise TypeError("Missed required keyword argument: {}".format(
                                k))

        for k in self._kwargs:
            setattr(self, k, None)

        for k in kwargs:
            if k not in self._kwargs:
                raise TypeError("Unknown keyword argument: {}".format(k))
            setattr(self, k, kwargs[k])

        # pylint: disable=access-member-before-definition
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.StreamHandler())

        # what we use to set flags on the original spam in imapbox
        self.spamflagscmd = "+FLAGS.SILENT"

    @property
    def cmd_save(self):
        """Is the command that dumps out a munged message including report."""
        if self.spamc:  # pylint: disable=no-member
            return ["spamc"]
        return ["spamassassin"]

    @property
    def cmd_test(self):
        """Is the command to use to test if the message is spam."""
        if self.spamc:  # pylint: disable=no-member
            return ["spamc", "-c"]
        return ["spamassassin", "--exit-code"]

    @classmethod
    def create_from_isbg(cls, sbg):
        """Return a instance with the required args from ```ISBG```.

        Args:
            sbg (isbg.ISBG): His attributes will be used to initialize a
                SpamAssassin instance.
        Returns:
            SpamAssassin: A new created object with the required attributes
                based based `sbg` attributes.

        """
        kw = dict()
        for k in cls._kwargs:
            kw[k] = getattr(sbg, k)
        return SpamAssassin(**kw)

    @staticmethod
    def get_formated_uids(uids, origpastuids, partialrun):
        """Get the uids formated.

        Args:
            uids (list(str)): The new ``uids``. It's formated as:
                ```['1 2 3 4']```
            origpastuids (list(int)): The original past ``uids``.
            partialrun (int): If not none the number of ``uids`` to return.
        Returns:
            list(str): The ``uids`` formated.

            It sorts the uids, remove those that are in `origpastuids` and
            returns the number defined by `partialrun`. If `partialrun` is
            ```None``` it return all.

        """
        uids = sorted(uids[0].split(), key=int, reverse=True)
        newpastuids = [u for u in origpastuids if str(u) in uids]
        uids = [u for u in uids if int(u) not in newpastuids]
        # Take only X elements if partialrun is enabled
        if partialrun:
            uids = uids[:int(partialrun)]
        return uids, newpastuids

    def learn(self, folder, learn_type, move_to, origpastuids):
        """Learn the spams (and if requested deleted or move them).

        Args:
            folder (str): The IMAP folder.
            leart_type (str): ```spam``` to learn spam, ```ham``` to learn
                nonspam.
            move_to (str): If not ```None```, the imap folder where the emails
                will be moved.
            origpastuids (list(int)): ``uids`` to not process.
        Returns:
            Sa_Learn:
                It contains the information about the result of the process.

            It will call ``spamc`` to learn the emails.

        Raises:
            isbg.ISBGError: if learn_type is unknown.


        TODO:
            Add suport to ``learn_type=forget``.

        """
        sa_learning = Sa_Learn()

        # Sanity checks:
        if learn_type not in ['spam', 'ham']:
            raise isbg.ISBGError(-1, message="Unknown learn_type")
        if self.imap is None:
            raise isbg.ISBGError(-1, message="Imap is required")

        self.logger.debug(__(
            "Teach {} to SA from: {}".format(learn_type, folder)))

        self.imap.select(folder)
        if self.learnunflagged:
            _, uids = self.imap.uid("SEARCH", None, "UNFLAGGED")
        elif self.learnflagged:
            _, uids = self.imap.uid("SEARCH", None, "(FLAGGED)")
        else:
            _, uids = self.imap.uid("SEARCH", None, "ALL")

        uids, sa_learning.newpastuids = SpamAssassin.get_formated_uids(
            uids, origpastuids, self.partialrun)

        sa_learning.tolearn = len(uids)

        for uid in uids:
            mail = imaputils.get_message(self.imap, uid, logger=self.logger)

            # Unwrap spamassassin reports
            unwrapped = sa_unwrap.unwrap(mail)
            if unwrapped is not None:
                self.logger.debug(__("{} Unwrapped: {}".format(
                    uid, utils.shorten(imaputils.mail_content(
                        unwrapped[0]), 140))))

            if unwrapped is not None and unwrapped:  # len(unwrapped)>0
                mail = unwrapped[0]

            if self.dryrun:
                code, code_orig = (0, 0)
            else:
                code, code_orig = learn_mail(mail, learn_type)

            if code == -9999:  # error processing email, try next.
                self.logger.exception(__(
                    'spamc error for mail {}'.format(uid)))
                self.logger.debug(repr(imaputils.mail_content(mail)))
                continue

            if code in [69, 74]:
                raise isbg.ISBGError(
                    isbg.__exitcodes__['flags'],
                    "spamassassin is misconfigured (use --allow-tell)")

            if code == 5:  # learned.
                sa_learning.learned += 1
                self.logger.debug(__(
                    "Learned {} (spamc return code {})".format(uid,
                                                               code_orig)))

            elif code == 6:  # already learned.
                self.logger.debug(__(
                    "Already learned {} (spamc return code {})".format(
                        uid, code_orig)))

            elif code == 98:  # too big.
                self.logger.warning(__(
                    "{} is too big (spamc return code {})".format(
                        uid, code_orig)))

            else:
                raise isbg.ISBGError(-1, ("{}: Unknown return code {} from " +
                                          "spamc").format(uid, code_orig))

            sa_learning.uids.append(int(uid))

            if not self.dryrun:
                if self.learnthendestroy:
                    if self.gmail:
                        self.imap.uid("COPY", uid, "[Gmail]/Trash")
                    else:
                        self.imap.uid("STORE", uid, self.spamflagscmd,
                                      "(\\Deleted)")
                elif move_to is not None:
                    self.imap.uid("COPY", uid, move_to)
                elif self.learnthenflag:
                    self.imap.uid("STORE", uid, self.spamflagscmd,
                                  "(\\Flagged)")

        return sa_learning

    def _process_spam(self, uid, score, mail, spamdeletelist):
        self.logger.debug(__("{} is spam".format(uid)))

        if (self.deletehigherthan is not None and
                float(score.split('/')[0]) > self.deletehigherthan):
            spamdeletelist.append(uid)
            return False

        # do we want to include the spam report
        if self.noreport is False:
            if self.dryrun:
                self.logger.info("Skipping report because of --dryrun")
            else:
                new_mail, code = feed_mail(mail, cmd=self.cmd_save)
                if new_mail == u"-9999":
                    self.logger.exception(
                        '{} error for mail {} (ret code {})'.format(
                            self.cmd_save, uid, code))
                    self.logger.debug(repr(imaputils.mail_content(mail)))
                    if uid in spamdeletelist:
                        spamdeletelist.remove(uid)
                    return False

                res = self.imap.append(self.imapsets.spaminbox, None, None,
                                       new_mail)
                # The above will fail on some IMAP servers for various
                # reasons. We print out what happened and continue
                # processing
                if res[0] != 'OK':
                    self.logger.error(__(
                        ("{} failed for uid {}: {}. Leaving original" +
                         "message alone.").format(
                            repr(["append", self.imapsets.spaminbox,
                                  "{email}"]),
                            repr(uid), repr(res))))
                    if uid in spamdeletelist:
                        spamdeletelist.remove(uid)
                    return False
        else:
            # No report:
            if self.dryrun:
                self.logger.info("Skipping copy to spambox because" +
                                 " of --dryrun")
            else:
                # just copy it as is
                self.imap.uid("COPY", uid, self.imapsets.spaminbox)

        return True

    def process_inbox(self, origpastuids):
        """Run spamassassin in the folder for spam."""
        sa_proc = Sa_Process()

        spamlist = []
        spamdeletelist = []

        # select inbox
        self.imap.select(self.imapsets.inbox, 1)

        # get the uids of all mails with a size less then the maxsize
        _, uids = self.imap.uid("SEARCH", None, "SMALLER", str(self.maxsize))

        uids, sa_proc.newpastuids = SpamAssassin.get_formated_uids(
            uids, origpastuids, self.partialrun)

        self.logger.debug(__('Got {} mails to check'.format(len(uids))))

        if self.dryrun:
            processednum = 0
            fakespammax = 1
            processmax = 5

        # Main loop that iterates over each new uid we haven't seen before
        for uid in uids:
            # Retrieve the entire message
            mail = imaputils.get_message(self.imap, uid, sa_proc.uids,
                                         logger=self.logger)

            # Unwrap spamassassin reports
            unwrapped = sa_unwrap.unwrap(mail)
            if unwrapped is not None and unwrapped:  # len(unwrapped) > 0
                mail = unwrapped[0]

            # Feed it to SpamAssassin in test mode
            if self.dryrun:
                if processednum > processmax:
                    break
                if processednum < fakespammax:
                    self.logger.info("Faking spam mail")
                    score = "10/10"
                    code = 1
                else:
                    self.logger.info("Faking ham mail")
                    score = "0/10"
                    code = 0
                processednum = processednum + 1
            else:
                score, code = test_mail(mail, cmd=self.cmd_test)
                if score == "-9999":
                    self.logger.exception(__(
                        '{} error for mail {}'.format(self.cmd_test, uid)))
                    self.logger.debug(repr(mail))
                    uids.remove(uid)
                    continue

            if score == "0/0\n":
                raise isbg.ISBGError(isbg.__exitcodes__['spamc'],
                                     "spamc -> spamd error - aborting")

            self.logger.debug(__(
                "Score for uid {}: {}".format(uid, score.strip())))

            if code != 0:
                # Message is spam, delete it or move it to spaminbox
                # (optionally with report)
                if not self._process_spam(uid, score, mail, spamdeletelist):
                    continue
                spamlist.append(uid)

        sa_proc.nummsg = len(uids)
        sa_proc.spamdeleted = len(spamdeletelist)
        sa_proc.numspam = len(spamlist) + sa_proc.spamdeleted

        # If we found any spams, now go and mark the original messages
        if sa_proc.numspam or sa_proc.spamdeleted:
            if self.dryrun:
                self.logger.info('Skipping labelling/expunging of mails ' +
                                 ' because of --dryrun')
            else:
                self.imap.select(self.imapsets.inbox)
                # Only set message flags if there are any
                if self.spamflags:  # len(self.smpamflgs) > 0
                    for uid in spamlist:
                        self.imap.uid("STORE", uid, self.spamflagscmd,
                                      imaputils.imapflags(self.spamflags))
                        sa_proc.newpastuids.append(uid)
                # If its gmail, and --delete was passed, we actually copy!
                if self.delete and self.gmail:
                    for uid in spamlist:
                        self.imap.uid("COPY", uid, "[Gmail]/Trash")
                # Set deleted flag for spam with high score
                for uid in spamdeletelist:
                    if self.gmail is True:
                        self.imap.uid("COPY", uid, "[Gmail]/Trash")
                    else:
                        self.imap.uid("STORE", uid, self.spamflagscmd,
                                      "(\\Deleted)")
                if self.expunge:
                    self.imap.expunge()

        return sa_proc
