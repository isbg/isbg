#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
isbg scans an IMAP Inbox and runs every entry against SpamAssassin.

For any entries that match, the message is copied to another folder, and the
original marked or deleted.

.. autodata:: __version__

.. autodata:: __exitcodes__
    :annotation: = {'ok': 0, ...}

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import os
import sys     # Because sys.stderr.write() is called bellow

from isbg import imaputils
from isbg import secrets
from isbg import spamproc
from isbg import utils

from .utils import __

import atexit
import getpass
import json
import logging
import re
import time

# xdg base dir specification (only xdg_cache_home is used)
try:
    from xdg.BaseDirectory import xdg_cache_home
except ImportError:
    xdg_cache_home = ""    # pylint: disable=invalid-name
if xdg_cache_home == "":
    # pylint: disable=invalid-name
    xdg_cache_home = os.path.expanduser("~" + os.sep + ".cache")
    """str: From the `XDG Base Directory specification`_.

We used this directory to create a `isbg/` one to store cached data:
    * lock file.
    * password file.
    * chached lists of ``uids``.

Note:
    For best `xdg_cache_home` detection, install *python-xdg*.

.. _XDG Base Directory specification:
    https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
"""


__version__ = "2.1.1"  #: The current isbg version

__license__ = \
    """License GPLv3: GNU GPL version 3 https://gnu.org/licenses/gpl.html

This is free software: you are free to change and redistribute it. There is NO
WARRANTY, to the extent permitted by law."""

__exitcodes__ = {
    'ok': 0,
    'newmsgs': 1,
    'newspam': 2,
    'newmsgspam': 3,
    'flags': 10,
    'imap': 11,
    'spamc': 12,
    'tty': 20,
    'locked': 30,
    'error': -1
}
"""Exit codes used as return in the command line usage in
:py:func:`sys.exit`.

================ === ========= ===============================================
Key              Val cmd? [1]_ Description
================ === ========= ===============================================
``'ok'``           0    no     All has finished ok.
``'newmsgs'``      1   yes     There was at least one new message, and none of
                               them were spam.
``'newspam'``      2   yes     There was at least one new message,
                               and all them were spam.
``'newmsgspam'``   3   yes     There were new messages, with at least one spam
                               and one non-spam.
``'flags'``       10    no     Error with the command line options.
``'imap'``        11    no     The IMAP server reported an error or error
                               with the IMAP connection.
``'spamc'``       12    no     Error with spamc/spamassassin call.
``'tty'``         20    no     The program was not launched in an interactive
                               terminal.
``'locked'``      30    no     Error with the *lock* file, is another instance
                               of ``isbg`` must be running.
``'error'``       -1    no     Other errors.
================ === ========= ===============================================

.. [1] ``--exitcodes`` required.
"""


class ISBGError(Exception):
    """Class for the ISBG exceptions.

    Attributes:
        exitcode (int): The exit code for the error.
        message (str): The human readable error message.

    """

    def __init__(self, exitcode=0, message=""):
        """Initialize a ISBGError object.

        Args:
            exitcode (int): Exit code. It must be a
                :py:const:`~isbg.isbg.__exitcodes__` valid value.
            message (str): Human readable error message.
        Raises:
            ValueError: If the `exitcode` is not in `__exitcodes__`.

        """
        self.exitcode = exitcode
        self.message = message

        Exception.__init__(self, message)
        if exitcode not in __exitcodes__.values():
            raise ValueError


class ISBG(object):
    """Main ISBG class.

    See also:
        :py:mod:`isbg.__main__` for command line usage.

    Examples:
        >>> import isbg
        >>> sbg = isbg.ISBG()
        >>> sbg.imapsets.host = "imap.example.org"
        >>> sbg.imapsets.port = 993
        >>> sbg.imapsets.user = "example@example.org"
        >>> sbg.imapsets.passwd = "xxxxxxxx"
        >>> sbg.imapsets.inbox = "INBOX"
        >>> sbg.imapsets.spaminbox = "INBOX.Spam"
        >>> sbg.imapsets.learnspambox = "INBOX.Spam"
        >>> sbg.imapsets.learnhambox = "NOSPAM"
        >>> # Set the number of mails to chech
        >>> sbg.partialrun = 4        # Only check 4 mails for every proc.
        >>> sbg.verbose = True        # Show more info
        >>> sbg.ignorelockfile = True # Ignore lock file
        >>> sbg.removelock()          # if there is a lock file
        >>> sbg.do_isbg()      # Connects to the imap and checks for spam

    Attributes:
        imap (isbg.imaputils.IsbgImap4): class that take care of connection
            and communication with the `IMAP` server. It's initialized calling
            :py:meth:`do_imap_login` and every time that calling
            :py:meth:`do_isbg`.
        imapsets (isbg.imaputils.ImapSettings): Object to store the `IMAP`
            settings. It's initialized when `ISBG` is initialized and also
            stores the IMAP folders used by ISBG.

            It also stores the command line args for:
                :py:attr:`~isbg.imaputils.ImapSettings.user` (imapuser),
                :py:attr:`~isbg.imaputils.ImapSettings.passwd` (imappasswd),
                :py:attr:`~isbg.imaputils.ImapSettings.host` (imaphost),
                :py:attr:`~isbg.imaputils.ImapSettings.port` (imapport),
                :py:attr:`~isbg.imaputils.ImapSettings.nossl` (nossl),
                :py:attr:`~isbg.imaputils.ImapSettings.inbox` (imapinbox),
                :py:attr:`~isbg.imaputils.ImapSettings.spaminbox` (spaminbox),
                :py:attr:`~isbg.imaputils.ImapSettings.learnspambox`
                (learnspambox) and
                :py:attr:`~isbg.imaputils.ImapSettings.learnhambox`
                (learnhambox).

        logger (logging.Logger): Object used to output info. It's initialized
            when `ISBG` is initialized.

    These are attributes derived from the command line and needed for normal
    operations:

    Attributes:
        exitcodes (bool): If True returns more exit codes. Defaults to
            ``True``.
        imaplist (bool): If True shows the folder list. Default to ``False``.
        noreport (bool): If True not adds SpamAssassin report to mails.
            Default to ``False``.
        nostats (bool): If True no shows stats. Default to ``False``.
        verbose_mails (bool): If True shows the email content. Default to
            ``False``.
        verbose: a property that if it's set to True show more information.
            Default to ``False``.

    These are attributes derived for the command line, and needed for
    `SpamAssassin` operations:

    Attributes:
        dryrun (bool): If True don't do changes in the IMAP account. Default to
            ``False``.
        maxsize (int): Max file size to process. Default to ``120,000``.
        teachonly (bool): If True don't search spam, only learn. Default to
            ``False``.
        spamc (bool): If True use spamc instead of standalone SpamAssassin.
            Default to ``False``.
        gmail (bool): If True Delete by copying to `[Gmail]/Trash` folder.
            Default to ``False``.
        deletehigherthan (float): If it's not None, the minimum score from a
            mail to be deleted. Default to ``None``.
        delete (bool): If True the spam mails will be marked for deletion.
            Default to ``False``.
        expunge (bool): If True causes marked for deletion messages to also
            be deleted (only useful if `deleted` is True. Default to ``None``.
        flag (bool): If True the spams will be flagged in your INBOX. Default
            to ``False``.
        learnflagged (bool): If True only learn flagged messages. Default to
            ``False``.
        learnunflagged (bool): If True only learn unflagged messages. Default
            to ``False``.
        learnthendestroy (bool): If True mark learned messages for deletion.
            Default to ``False``.
        learnthenflag (bool): If True flag learned messages. Default to
            ``False``.
        movehamto (str): If it's not None, IMAP folder where the ham mail will
            be moved. Default to ``None``.

    These are attributes derived from the command line and related to the lock
    file:

    Attributes:
        ignorelockfile (bool): If True and there is the lock file a error is
            raised.
        lockfile (str): Full path and name of the lock file.

            The path it's initialized with the xdg cache home specification
            plus `/isbg/` and with the name ``lock``.

        lockfilegrace (float): Lifetime of the lock file in seconds. Default to
            240.0

    These are attributes derived for the command line, related to the
    `IMAP` password and files:

    Attributes:
        passwdfilename (str): The fill name where the password will be stored.
            Defaults to ``None``. It only have use if `savepw` is `True`.
        savepw (bool): If True a obfuscated password will be stored into a
            file.
        trackfile (str): Base name where the processed ``uids`` will be stored
            to not reprocess them. Default to ``None`` when initialized and
            initialized the first time that is needed.

    """

    def __init__(self):
        """Initialize a ISBG object."""
        self.imapsets = imaputils.ImapSettings()
        self.imap = None

        # FIXME: This could be used when ran non-interactively, maybe with
        # the --noninteractive argument (instead of the addHandler:
        # logging.basicConfig(
        #    format=('%(asctime)s %(levelname)-8s [%(filename)s'
        #            + '%(lineno)d] %(message)s'),
        #    datefmt='%Y%m%d %H:%M:%S %Z')
        # see https://docs.python.org/2/howto/logging-cookbook.html
        self.logger = logging.getLogger(__name__)       #: a logger
        self.logger.addHandler(logging.StreamHandler())

        # We create the dir for store cached information (if needed)
        if not os.path.isdir(os.path.join(xdg_cache_home, "isbg")):
            os.makedirs(os.path.join(xdg_cache_home, "isbg"))

        self.imaplist, self.nostats = (False, False)
        self.noreport, self.exitcodes = (False, True)
        self.verbose_mails, self._verbose = (False, False)
        self._set_loglevel(logging.INFO)
        # Processing options:
        self.dryrun, self.maxsize, self.teachonly = (False, 120000, False)
        self.spamc, self.gmail = (False, False)
        # spamassassin options:
        self.movehamto, self.delete = (None, False)
        self.deletehigherthan, self.flag, self.expunge = (None, False, False)
        # Learning options:
        self.learnflagged, self.learnunflagged = (False, False)
        self.learnthendestroy, self.learnthenflag = (False, False)
        # Lockfile options:
        self.ignorelockfile = False
        self.lockfilename = os.path.join(xdg_cache_home, "isbg", "lock")
        self.lockfilegrace = 240.0
        # Password options (a vague level of obfuscation):
        self.passwdfilename, self.savepw = (None, False)
        # Trackfile options:
        self.trackfile, self.partialrun = (None, 50)

        try:
            self.interactive = sys.stdin.isatty()
        except AttributeError:
            self.logger.warning("Can't get info about if stdin is a tty")
            self.interactive = False

        # what we use to set flags on the original spam in imapbox
        self.spamflagscmd = "+FLAGS.SILENT"
        # and the flags we set them to (none by default)
        self.spamflags = []

    @staticmethod
    def set_filename(imapsets, filetype):
        """Set the filename of cached created files.

        If `filetype` is password, the file name start with `.isbg-`, else
        it starts with the filetype. A hash from the imapsets it's appended
        to it. The path of the file will be ``xdg_cache_home``/isbg/

        Args:
            imapsets (isbg.imaputils.ImapSettings): Imap setings instance.
            filetype (str): The file type.
        Returns:
            str: The full file path.

        """
        if filetype == "password":
            filename = os.path.join(xdg_cache_home, "isbg", ".isbg-")
        else:
            filename = os.path.join(xdg_cache_home, "isbg", filetype)
        return filename + imapsets.hash.hexdigest()

    @property
    def verbose(self):
        """Get the verbose property.

        :getter: Gets the verbose property.
        :setter: Sets verbose property.
        :type: bool.
        """
        return self._verbose

    @verbose.setter
    def verbose(self, newval):
        """Set the verbose property and the required log level."""
        self._verbose = newval
        if self._verbose:
            self._set_loglevel(logging.DEBUG)
        else:
            self._set_loglevel(logging.INFO)

    def _set_loglevel(self, level):
        """Set the log level."""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)

    def removelock(self):
        """Remove the lockfile."""
        if os.path.exists(self.lockfilename):
            os.remove(self.lockfilename)

    def assertok(self, res, *args):
        """Check that the return code is OK.

        It also prints out what happened (which would end
        up /dev/null'ed in non-verbose mode)
        """
        if 'uid FETCH' in args[0] and not self.verbose_mails:
            res = utils.shorten(res, 140)
        if 'SEARCH' in args[0]:
            res = utils.shorten(res, 140)
        self.logger.debug("{} = {}".format(args, res))
        if res[0] not in ["OK", "BYE"]:
            self.logger.error(
                __("{} returned {} - aborting".format(args, res)))
            raise ISBGError(__exitcodes__['imap'] if self.exitcodes else -1,
                            "\n%s returned %s - aborting\n" % (repr(args), res)
                            )

    def pastuid_read(self, uidvalidity, folder='inbox'):
        """Read the uids stored in a file for  a folder.

        pastuids_read keeps track of which uids we have already seen, so
        that we don't analyze them multiple times. We store its
        contents between sessions by saving into a file as Python
        code (makes loading it here real easy since we just source
        the file)
        """
        if self.trackfile is None:
            self.trackfile = ISBG.set_filename(self.imapsets, "track")
        pastuids = []
        try:
            with open(self.trackfile + folder, 'r') as rfile:
                struct = json.load(rfile)
                if struct['uidvalidity'] == uidvalidity:
                    pastuids = struct['uids']
        except Exception:  # pylint: disable=broad-except
            pass
        return pastuids

    def pastuid_write(self, uidvalidity, origpastuids, newpastuids,
                      folder='inbox'):
        """Write the uids in a file for the folder."""
        if self.trackfile is None:
            self.trackfile = ISBG.set_filename(self.imapsets, "track")

        wfile = open(self.trackfile + folder, "w+")
        try:
            os.chmod(self.trackfile + folder, 0o600)
        except Exception:  # pylint: disable=broad-except
            pass
        self.logger.debug(__(('Writing pastuids for folder {}: {} ' +
                              'origpastuids, newpastuids: {}').format(
            folder, len(origpastuids), newpastuids)))
        struct = {
            'uidvalidity': uidvalidity,
            'uids': list(set(newpastuids + origpastuids))
        }
        json.dump(struct, wfile)
        wfile.close()

    def _do_lockfile_or_raise(self):
        """Create the lockfile or raise a error if it exists."""
        if (os.path.exists(self.lockfilename) and
                (os.path.getmtime(self.lockfilename) +
                    (self.lockfilegrace * 60) > time.time())):
            raise ISBGError(__exitcodes__['locked'],
                            "Lock file is present. Guessing isbg is " +
                            "already running. Exit.")
        else:
            lockfile = open(self.lockfilename, 'w')
            lockfile.write(repr(os.getpid()))
            lockfile.close()

            #: FIXME: May be found a better way that use of atexit
            # Make sure to delete lock file
            atexit.register(self.removelock)

    def _do_get_password(self):
        """Get the password from file or prompt for it."""
        if (self.savepw is False and
                os.path.exists(self.passwdfilename) is True):
            try:
                sec = secrets.SecretIsbg(filename=self.passwdfilename,
                                         imapset=self.imapsets)
                self.imapsets.passwd = sec.get("password")
                del sec
                self.logger.debug("Successfully read password file")
            except Exception:  # pylint: disable=broad-except
                self.logger.exception('Error reading pw!')

        # do we have to prompt?
        if self.imapsets.passwd is None:
            if not self.interactive:
                raise ISBGError(__exitcodes__['ok'],
                                "You need to specify your imap password " +
                                "and save it with the --savepw switch")
            self.imapsets.passwd = getpass.getpass(
                "IMAP password for %s@%s: " % (
                    self.imapsets.user, self.imapsets.host))

    def _do_save_password(self):
        """Save password to the password file."""
        try:
            sec = secrets.SecretIsbg(filename=self.passwdfilename,
                                     imapset=self.imapsets)
            sec.set("password", self.imapsets.passwd)
            del sec
        except Exception:  # pylint: disable=broad-except
            self.logger.exception('Error saving pw!')

    def do_list_imap(self):
        """List the imap boxes."""
        imap_list = self.imap.list()
        dirlist = str([x.decode() for x in imap_list[1]])
        # string formatting
        dirlist = re.sub(r'\(.*?\)| \".\" \"|\"\', \'', " ", dirlist)
        self.logger.info(dirlist)

    def do_spamassassin(self):
        """Do the spamassassin procesing.

        It creates a instance of :py:class:`~isbg.spamproc.SpamAssassin`
        every time that this method is called. The ``SpamAssasssin`` object
        would contact to the IMAP server to get the emails and to
        ``SpamAssassin`` command line to process them.

        """
        sa = spamproc.SpamAssassin.create_from_isbg(self)

        # SpamAssassin training: Learn spam
        s_learned = spamproc.Sa_Learn()
        if self.imapsets.learnspambox:
            uidvalidity = self.imap.get_uidvalidity(self.imapsets.learnspambox)
            origpastuids = self.pastuid_read(uidvalidity, 'spam')
            s_learned = sa.learn(self.imapsets.learnspambox, 'spam', None,
                                 origpastuids)
            self.pastuid_write(uidvalidity, s_learned.newpastuids,
                               s_learned.uids, 'spam')

        # SpamAssassin training: Learn ham
        h_learned = spamproc.Sa_Learn()
        if self.imapsets.learnhambox:
            uidvalidity = self.imap.get_uidvalidity(self.imapsets.learnhambox)
            origpastuids = self.pastuid_read(uidvalidity, 'ham')
            h_learned = sa.learn(self.imapsets.learnhambox, 'ham',
                                 self.movehamto, origpastuids)
            self.pastuid_write(uidvalidity, h_learned.newpastuids,
                               h_learned.uids, 'ham')

        if not self.teachonly:
            # check spaminbox exists by examining it
            self.imap.select(self.imapsets.spaminbox, 1)

            uidvalidity = self.imap.get_uidvalidity(self.imapsets.inbox)
            origpastuids = self.pastuid_read(uidvalidity)
            proc = sa.process_inbox(origpastuids)
            self.pastuid_write(uidvalidity, proc.newpastuids, proc.uids)

        if self.nostats is False:
            if self.imapsets.learnspambox is not None:
                self.logger.info(__(
                    "{}/{} spams learned".format(s_learned.learned,
                                                 s_learned.tolearn)))
            if self.imapsets.learnhambox:
                self.logger.info(__(
                    "{}/{} hams learned".format(h_learned.learned,
                                                h_learned.tolearn)))
            if not self.teachonly:
                self.logger.info(__(
                    "{} spams found in {} messages".format(proc.numspam,
                                                           proc.nummsg)))
                self.logger.info(__("{}/{} was automatically deleted".format(
                    proc.spamdeleted, proc.numspam)))

        return proc

    def do_imap_login(self):
        """Login to the imap."""
        self.imap = imaputils.login_imap(self.imapsets,
                                         logger=self.logger,
                                         assertok=self.assertok)

    def do_imap_logout(self):
        """Sign off from the imap connection."""
        self.imap.logout()

    def do_isbg(self):
        """Execute the main isbg process.

        It should be called to process the IMAP account. It returns a
        exitcode if its called from the command line and have the --exitcodes
        param.
        """
        if self.delete and not self.gmail and \
                "\\Deleted" not in self.spamflags:
            self.spamflags.append("\\Deleted")

        if self.trackfile is None:
            self.trackfile = ISBG.set_filename(self.imapsets, "track")

        if self.passwdfilename is None:
            self.passwdfilename = ISBG.set_filename(self.imapsets, "password")

        self.logger.debug(__("Lock file is {}".format(self.lockfilename)))
        self.logger.debug(__("Trackfile starts with {}".format(self.trackfile))
                          )
        self.logger.debug(__(
            "Password file is {}".format(self.passwdfilename)))
        self.logger.debug(__("SpamFlags are {}".format(self.spamflags)))

        # Acquire lockfilename or exit
        if self.ignorelockfile:
            self.logger.debug("Lock file is ignored. Continue.")
        else:
            self._do_lockfile_or_raise()

        # Figure out the password
        if self.imapsets.passwd is None:
            self._do_get_password()

        # ***** Main code starts here *****

        # Connection with the imaplib server
        self.do_imap_login()

        # Should we save it?
        if self.savepw:
            self._do_save_password()

        if self.imaplist:
            # List imap directories
            self.do_list_imap()
        else:
            # Spamassasin training and processing:
            proc = self.do_spamassassin()

        # sign off
        self.do_imap_logout()

        if self.exitcodes and __name__ == '__main__':
            if not self.teachonly:
                if proc.numspam == 0:
                    return __exitcodes__['newmsgs']
                if proc.numspam == proc.nummsg:
                    return __exitcodes__['newspam']
                return __exitcodes__['newmsgspam']

            return __exitcodes__['ok']
