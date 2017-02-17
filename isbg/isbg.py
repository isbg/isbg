#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
isbg scans an IMAP Inbox and runs every entry against SpamAssassin.
For any entries that match, the message is copied to another folder,
and the original marked or deleted.

This software was mainly written Roger Binns <rogerb@rogerbinns.com>
and maintained by Thomas Lecavelier <thomas@lecavelier.name> since
novembre 2009. You may use isbg under any OSI approved open source
license such as those listed at http://opensource.org/licenses/alphabetical

Usage:
    isbg.py [options]
    isbg.py (-h | --help)
    isbg.py --version

Options:
    --dryrun             Do not actually make any changes
    --delete             The spams will be marked for deletion from your inbox
    --deletehigherthan # Delete any spam with a score higher than #
    --exitcodes          Use exitcodes to detail  what happened
    --expunge            Cause marked for deletion messages to also be deleted
                         (only useful if --delete is specified)
    --flag               The spams will be flagged in your inbox
    --gmail              Delete by copying to '[Gmail]/Trash' folder
    --help               Show the help screen
    --ignorelockfile     Don't stop if lock file is present
    --imaphost hostname  IMAP server name
    --imaplist           List imap directories
    --imappasswd passwd  IMAP account password
    --imapport port      Use a custom port
    --imapuser username  Who you login as
    --imapinbox mbox     Name of your inbox folder
    --learnspambox mbox  Name of your learn spam folder
    --learnhambox mbox   Name of your learn ham folder
    --learnthendestroy   Mark learnt messages for deletion
    --learnthenflag      Flag learnt messages
    --learnunflagged     Only learn if unflagged (for --learnthenflag)
    --learnflagged       Only learn flagged
    --lockfilegrace #    Set the lifetime of the lock file to # (in minutes)
    --lockfilename file  Override the lock file name
    --maxsize numbytes   Messages larger than this will be ignored as they are
                         unlikely to be spam
    --movehamto mbox     Move ham to folder
    --noninteractive     Prevent interactive requests
    --noreport           Don't include the SpamAssassin report in the message
                         copied to your spam folder
    --nostats            Don't print stats
    --partialrun num     Stop operation after scanning 'num' unseen emails
    --passwdfilename fn  Use a file to supply the password
    --savepw             Store the password to be used in future runs
    --spamc              Use spamc instead of standalone SpamAssassin binary
    --spaminbox mbox     Name of your spam folder
    --nossl              Don't use SSL to connect to the IMAP server
    --teachonly          Don't search spam, just learn from folders
    --trackfile file     Override the trackfile name
    --verbose            Show IMAP stuff happening
    --verbose-mails      Show mail bodies (extra-verbose)
    --version            Show the version information

    (Your inbox will remain untouched unless you specify --flag or --delete)

"""

import sys  # Because sys.stderr.write() is called bellow
from io import BytesIO

# FIXME: This is necessary to allow using isbg both straight from the repo and installed / as an import.
# We should probably decide to not care about running isbg as top-level script straight from the repo.
try:
    from .sa_unwrap import unwrap
except:
    try:
        from sa_unwrap import unwrap
    except ImportError:
        sys.stderr.write('Cannot load sa_unwrap, please install isbg package properly!\n')
        # Create No-Op dummy function
        unwrap = lambda x: None

try:
    from docopt import docopt  # Creating command-line interface
except ImportError:
    sys.stderr.write("Missing dependency: docopt\n")
    raise

from subprocess import Popen, PIPE

import imaplib
import re
import os
import getpass
import string
import time
import atexit
import json
import logging

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

class ISBGError(Exception):
    pass

def errorexit(msg, exitcode):
    sys.stderr.write(msg)
    sys.stderr.write("\nUse --help to see valid options and arguments\n")
    if exitcode == -1:
        raise ISBGError((exitcode, msg))
    sys.exit(exitcode)

def hexof(x):
    res = ""
    for i in x:
        res = res + ("%02x" % ord(i))
    return res

def hexdigit(c):
    if c >= '0' and c <= '9':
        return ord(c)-ord('0')
    if c >= 'a' and c <= 'f':
        return 10 + ord(c) - ord('a')
    if c >= 'A' and c <= 'F':
        return 10 + ord(c) - ord('A')
    raise ValueError(repr(c) + " is not a valid hexadecimal digit")

def dehexof(x):
    res = ""
    while(len(x)):
        res = res + chr(16 * hexdigit(x[0]) + hexdigit(x[1]))
        x = x[2:]
    return res

# This function makes sure that each lines ends in <CR><LF>
# SpamAssassin strips out the <CR> normally
crnlre = re.compile("([^\r])\n", re.DOTALL)

def crnlify(text):
    # we have to do it twice to work right since the re includes
    # the char preceding \n
    return re.sub(crnlre, "\\1\r\n", re.sub(crnlre, "\\1\r\n", text))

def truncate(inp, length):
    if len(inp) > length:
        return repr(inp)[:length-3] + '...'
    else:
        return inp

def shorten(inp, length):
    if isinstance(inp, dict):
        return dict([(k, shorten(v, length)) for k,v in inp.items()])
    elif isinstance(inp, list) or isinstance(inp, tuple):
        return [ shorten(x, length) for x in inp]
    else:
        return truncate(inp, length)

def imapflags(flaglist):
    return '(' + ','.join(flaglist) + ')'

class ISBG:
    exitcodeok = 0          # all went well
    exitcodenewmsgs = 1     # there were new messages - none of them spam
    exitcodenewspam = 2     # they were all spam
    exitcodenewmsgspam = 3  # there were new messages and new spam
    exitcodeflags = 10      # there were errors in the command line arguments
    exitcodeimap = 11       # there was an IMAP level error
    exitcodespamc = 12      # error of communication between spamc and spamd
    exitcodetty = 20        # error because of non interative terminal
    exitcodelocked = 30     # there's certainly another isbg running

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.set_imap_opts(
            imaphost='localhost',
            imapport=143,
            imapuser='',
            imappasswd=None,
            nossl=False
        )
        self.set_mailboxes(
            inbox="INBOX",
            spaminbox="INBOX.spam",
            learnspambox=None,
            learnhambox=None
        )
        self.set_reporting_opts(
            imaplist=False,
            nostats=False,
            noreport=False,
            exitcodes=True,
            verbose=False,
            verbose_mails=False
        )
        self.set_processing_opts(
            dryrun=False,
            maxsize=120000,
            teachonly=False,
            spamc=False,
            gmail=False
        )
        self.set_lockfile_opts(
            ignorelockfile=False,
            lockfilename=os.path.expanduser("~" + os.sep + ".isbg-lock"),
            lockfilegrace=240
        )
        self.set_password_opts(
            passwdfilename=None,
            savepw=False
        )
        self.set_trackfile_opts(
            trackfile=None,
            partialrun=False
        )
        self.set_sa_opts(
            movehamto=None,
            delete=False,
            deletehigherthan=None,
            flag=False,
            expunge=False
        )
        self.set_learning_opts(
            learnflagged=False,
            learnunflagged=False,
            learnthendestroy=False,
            learnthenflag=False
        )

        self.interactive = sys.stdin.isatty()
        self.alreadylearnt = "Message was already un/learned"
        # satest is the command that is used to test if the message is spam
        self.satest = ["spamassassin", "--exit-code"]
        # sasave is the one that dumps out a munged message including report
        self.sasave = ["spamassassin"]
        # what we use to set flags on the original spam in imapbox
        self.spamflagscmd = "+FLAGS.SILENT"
        # and the flags we set them to (none by default)
        self.spamflags = []

        # ###
        # ### exitcode maps
        # ###

        # IMAP implementation detail
        # Courier IMAP ignores uid fetches where more than a certain number are listed
        # so we break them down into smaller groups of this size
        self.uidfetchbatchsize = 25
        # password saving stuff. A vague level of obfuscation
        self.passwdfilename = None
        self.passwordhash = None
        self.passwordhashlen = 256  # should be a multiple of 16

    def set_imap_opts(self, imaphost, imapport, imapuser, imappasswd, nossl):
        self.imaphost = imaphost
        self.imapport = imapport
        self.imapuser = imapuser
        self.imappasswd = imappasswd
        self.nossl = nossl

    def set_mailboxes(self, inbox, spaminbox, learnspambox, learnhambox):
        self.imapinbox = inbox
        self.spaminbox = spaminbox
        self.learnspambox = learnspambox
        self.learnhambox = learnhambox

    def set_reporting_opts(self, imaplist, nostats, noreport, exitcodes, verbose, verbose_mails):
        self.imaplist = imaplist
        self.nostats = nostats
        self.noreport = noreport
        self.exitcodes = exitcodes
        self.verbose = verbose
        self.verbose_mails = verbose_mails

    def set_processing_opts(self, dryrun, maxsize, teachonly, spamc, gmail):
        self.dryrun = dryrun
        self.maxsize = maxsize
        self.teachonly = teachonly
        self.spamc = spamc
        self.gmail = gmail

    def set_lockfile_opts(self, ignorelockfile, lockfilename, lockfilegrace):
        self.ignorelockfile = ignorelockfile
        self.lockfilename = lockfilename
        self.lockfilegrace = lockfilegrace

    def set_password_opts(self, passwdfilename, savepw):
        self.passwdfilename = passwdfilename
        self.savepw = savepw

    def set_trackfile_opts(self, trackfile, partialrun):
        self.pastuidsfile = trackfile
        self.partialrun = partialrun

    def set_sa_opts(self, movehamto, delete, deletehigherthan, flag, expunge):
        self.movehamto = movehamto
        self.delete = delete
        self.deletehigherthan = deletehigherthan
        self.flag = flag
        self.expunge = expunge

    def set_learning_opts(self, learnflagged, learnunflagged, learnthendestroy, learnthenflag):
        if learnflagged and learnunflagged:
            raise ValueError('Cannot pass learnflagged and learnunflagged at same time')
        self.learnflagged = learnflagged
        self.learnunflagged = learnunflagged
        self.learnthendestroy = learnthendestroy
        self.learnthenflag = learnthenflag

    def removelock(self):
        if os.path.exists(self.lockfilename):
            os.remove(self.lockfilename)

    # Password stuff
    def getpw(self, data, hash):
        res = ""
        for i in range(0, self.passwordhashlen):
            if isinstance(hash[i], int):
                c = ord(data[i]) ^ hash[i]
            else:
                c = ord(data[i]) ^ ord(hash[i])
            if c == 0:
                break
            res = res + chr(c)
        return res

    def setpw(self, pw, hash):
        if len(pw) > self.passwordhashlen:
            raise ValueError("""Password of length %d is too long to
                             store (max accepted is %d)"""
                             % (len(pw), self.passwordhashlen))
        res = list(hash)
        if isinstance(res[0], int):
            res = [chr(x) for x in res]
        for i in range(0, len(pw)):
            res[i] = chr(ord(res[i]) ^ ord(pw[i]))
        try:
            return string.join(res, '')
        except:
            return ''.join(res)

    # Retrieve the entire message
    def getmessage(self, uid, append_to=None):
        res = self.imap.uid("FETCH", uid, "(BODY.PEEK[])")
        self.assertok(res, 'uid fetch', uid, '(BODY.PEEK[])')
        if res[0] != "OK":
            self.assertok(res, 'uid fetch', uid, '(BODY.PEEK[])')
            try:
                body = res[1][0][1]
            except:
                self.exception('IMAP Message not in expected format!')
                if self.verbose:
                    self.logger.warning("Confused - rfc822 fetch gave {} - The message was probably deleted while we were running".format(res))
                if append_to is not None:
                    append_to.append(int(uid))
        else:
            body = res[1][0][1]
        return body

    # This function checks that the return code is OK
    # It also prints out what happened (which would end
    # up /dev/null'ed in non-verbose mode)
    def assertok(self, res, *args):
        if 'fetch' in args[0] and not self.verbose_mails:
            res = shorten(res, 100)
        self.logger.debug("{} = {}".format(args,res))
        if res[0] != "OK":
            self.logger.error("{} returned {} - aborting")
            errorexit("\n%s returned %s - aborting\n"
                      % (repr(args), res), self.exitcodeimap if self.exitcodes else -1)

    def parse_args(self):
        # Argument processing
        try:
            self.opts = docopt(__doc__, version="isbg version 1.00")
            self.opts = dict([(k,v) for k,v in self.opts.items() if v is not None])
        except Exception as e:
            errorexit("Option processing failed - " + str(e), self.exitcodeflags)


        if self.opts.get("--deletehigherthan") is not None:
            try:
                self.deletehigherthan = float(self.opts["--deletehigherthan"])
            except:
                errorexit("Unrecognized score - " + self.opts["--deletehigherthan"], self.exitcodeflags)
            if self.deletehigherthan < 1:
                errorexit("Score " + repr(self.deletehigherthan) + " is too small", self.exitcodeflags)
        else:
            self.deletehigherthan = None

        if self.opts["--flag"] is True:
            self.spamflags.append("\\Flagged")

        self.imaphost = self.opts.get('--imaphost', self.imaphost)
        self.imappasswd = self.opts.get('--imappasswd', self.imappasswd)
        self.imapport = self.opts.get('--imapport', self.imapport)
        self.imapuser = self.opts.get('--imapuser', self.imapuser)
        self.imapinbox = self.opts.get('--imapinbox', self.imapinbox)
        self.learnspambox = self.opts.get('--learnspambox')
        self.learnhambox = self.opts.get('--learnhambox')
        self.lockfilegrace = self.opts.get('--lockfilegrace', self.lockfilegrace)
        self.nostats = self.opts.get('--nostats', False)
        self.dryrun = self.opts.get('--dryrun', False)
        self.delete = self.opts.get('--delete', False)
        self.gmail = self.opts.get('--gmail', False)

        if self.opts.get("--maxsize") is not None:
            try:
                self.maxsize = int(self.opts["--maxsize"])
            except:
                errorexit("Unrecognised size - " + self.opts["--maxsize"], self.exitcodeflags)
            if self.maxsize < 1:
                errorexit("Size " + repr(self.maxsize) + " is too small", self.exitcodeflags)

        self.movehamto = self.opts.get('--movehamto')

        if self.opts["--noninteractive"] is True:
            self.interactive = 0

        self.noreport = self.opts.get('--noreport', self.noreport)

        self.spaminbox = self.opts.get('--spaminbox', self.spaminbox)

        self.lockfilename = self.opts.get('--lockfilename', self.lockfilename)

        self.pastuidsfile = self.opts.get('--trackfile', self.pastuidsfile)

        if self.opts.get("--partialrun") is not None:
            self.partialrun = int(self.opts["--partialrun"])
            if self.partialrun < 1:
                errorexit("Partial run number must be equal to 1 or higher", self.exitcodeflags)

        self.verbose = self.opts.get('--verbose', False)
        self.verbose_mails = self.opts.get('--verbose-mails', False)
        self.ignorelockfile = self.opts.get("--ignorelockfile", False)
        self.savepw = self.opts.get('--savepw', False)
        self.passwdfilename = self.opts.get('--passwdfilename', self.passwdfilename);

        self.nossl = self.opts.get('--nossl', False)
        self.imaplist = self.opts.get('--imaplist', False)

        self.learnunflagged = self.opts.get('--learnunflagged', False)
        self.learnflagged = self.opts.get('--learnflagged', False)
        self.learnthendestroy = self.opts.get('--learnthendestroy', False)
        self.learnthenflag = self.opts.get('--learnthendestroy', False)
        self.expunge = self.opts.get('--expunge', False)

        self.teachonly = self.opts.get('--teachonly', False)
        self.spamc = self.opts.get('--spamc', False)

        self.exitcodes = self.opts.get('--exitcodes', False)

        # fixup any arguments

        if self.opts.get("--imapport") is None:
            if self.opts["--nossl"] is True:
                self.imapport = 143
            else:
                self.imapport = 993

    def get_uidvalidity(self, mailbox):
        uidvalidity = 0
        mbstatus = self.imap.status(mailbox, '(UIDVALIDITY)')
        if mbstatus[0] == 'OK':
            body = mbstatus[1][0].decode()
            m = re.search('UIDVALIDITY ([0-9]+)', body)
            if m is not None:
                uidvalidity = int(m.groups()[0])
        return uidvalidity

    def pastuid_read(self, uidvalidity, folder='inbox'):
        # pastuids keeps track of which uids we have already seen, so
        # that we don't analyze them multiple times. We store its
        # contents between sessions by saving into a file as Python
        # code (makes loading it here real easy since we just source
        # the file)
        pastuids = []
        try:
            with open(self.pastuidsfile + folder, 'r') as f:
                struct = json.load(f)
                if struct['uidvalidity'] == uidvalidity:
                    pastuids = struct['uids']
        except:
            pass
        return pastuids

    def pastuid_write(self, uidvalidity, origpastuids, newpastuids, folder='inbox'):
        f = open(self.pastuidsfile + folder, "w+")
        try:
            os.chmod(self.pastuidsfile + folder, 0o600)
        except:
            pass
        self.logger.debug('Writing pastuids, {} origpastuids, newpastuids: {}'.format(len(origpastuids), newpastuids))
        struct = {
            'uidvalidity': uidvalidity,
            'uids': list(set(newpastuids + origpastuids))
        }
        json.dump(struct, f)
        f.close()

    def spamassassin(self):
        uids = []

        # check spaminbox exists by examining it
        res = self.imap.select(self.spaminbox, 1)
        self.assertok(res, 'select', self.spaminbox, 1)

        # select inbox
        res = self.imap.select(self.imapinbox, 1)
        self.assertok(res, 'select', self.imapinbox, 1)

        uidvalidity = self.get_uidvalidity(self.imapinbox)

        # get the uids of all mails with a size less then the maxsize
        typ, inboxuids = self.imap.uid("SEARCH", None, "SMALLER", str(self.maxsize))
        inboxuids = inboxuids[0].split()
        if sys.version_info.major >= 3:
            inboxuids = [x.decode() for x in inboxuids]

        # remember what pastuids looked like so that we can compare at the end
        origpastuids = self.pastuid_read(uidvalidity)
        newpastuids = []

        # filter away uids that was previously scanned
        uids = [u for u in inboxuids if u not in origpastuids]

        # Take only X elements if partialrun is enabled
        if self.partialrun:
            uids = uids[:int(self.partialrun)]

        self.logger.debug('Got {} mails to check'.format(len(uids)))

        # Keep track of new spam uids
        spamlist = []

        # Keep track of spam that is to be deleted
        spamdeletelist = []

        if self.dryrun:
            processednum = 0
            fakespammax = 1
            processmax = 5

        # Main loop that iterates over each new uid we haven't seen before
        for u in uids:
            # Retrieve the entire message
            body = self.getmessage(u, newpastuids)
            # Unwrap spamassassin reports
            unwrapped = unwrap(BytesIO(body))
            if unwrapped is not None and len(unwrapped) > 0:
                body = unwrapped[0]

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
                if os.name == 'nt':
                    p = Popen(self.satest, stdin=PIPE, stdout=PIPE)
                else:
                    p = Popen(self.satest, stdin=PIPE, stdout=PIPE, close_fds=True)
                try:
                    score = p.communicate(body)[0]
                    if sys.version_info.major >= 3:
                        score = score.decode()
                    if not self.spamc:
                        m = re.search("score=(-?\d+(?:\.\d+)?) required=(\d+(?:\.\d+)?)",
                                      score)
                        score = m.group(1) + "/" + m.group(2) + "\n"
                    code = p.returncode
                except:
                    self.logger.exception('Error communicating with {}!'.format(self.satest))
                    continue
            if score == "0/0\n":
                errorexit("spamc -> spamd error - aborting", self.exitcodespamc)

            self.logger.debug("[{}] score: {}".format(u, score))

            if code == 0:
                # Message is below threshold
                # but it was already appended by getmessage...???
                # self.pastuids.append(u)
                pass
            else:
                # Message is spam, delete it or move it to spaminbox (optionally with report)
                self.logger.debug("{} is spam".format(u))

                if (self.deletehigherthan is not None and
                            float(score.split('/')[0]) > self.deletehigherthan):
                    spamdeletelist.append(u)
                    continue

                # do we want to include the spam report
                if self.noreport is False:
                    if self.dryrun:
                        self.logger.info("Skipping report because of --dryrun")
                    else:
                        # filter it through sa
                        if os.name == 'nt':
                            p = Popen(self.sasave, stdin=PIPE, stdout=PIPE)
                        else:
                            p = Popen(self.sasave, stdin=PIPE, stdout=PIPE, close_fds=True)
                        try:
                            body = p.communicate(body)[0]
                        except:
                            self.logger.exception('Error communicating with {}!'.format(self.sasave))
                            continue
                        p.stdin.close()
                        body = crnlify(body)
                        res = self.imap.append(self.spaminbox, None, None, body)
                        # The above will fail on some IMAP servers for various reasons.
                        # we print out what happened and continue processing
                        if res[0] != 'OK':
                            self.logger.error("{} failed for uid {}: {}. Leaving original message alone.".format(repr(["append", self.spaminbox, "{body}"]), repr(u), repr(res)))
                            continue
                else:
                    if self.dryrun:
                        self.logger.info("Skipping copy to spambox because of --dryrun")
                    else:
                        # just copy it as is
                        res = self.imap.uid("COPY", u, self.spaminbox)
                        self.assertok(res, "uid copy", u, self.spaminbox)

                spamlist.append(u)

        self.pastuid_write(uidvalidity, origpastuids, newpastuids)

        nummsg = len(uids)
        spamdeleted = len(spamdeletelist)
        numspam = len(spamlist) + spamdeleted

        # If we found any spams, now go and mark the original messages
        if numspam or spamdeleted:
            if self.dryrun:
                self.logger.info('Skipping labelling/expunging of mails because of --dryrun')
            else:
                res = self.imap.select(self.imapinbox)
                self.assertok(res, 'select', self.imapinbox)
                # Only set message flags if there are any
                if len(spamflags) > 2:
                    for u in spamlist:
                        res = self.imap.uid("STORE", u, self.spamflagscmd, imapflags(self.spamflags))
                        self.assertok(res, "uid store", u, self.spamflagscmd, imapflags(spamflags))
                        newpastuids.append(u)
                # If its gmail, and --delete was passed, we actually copy!
                if self.delete and self.gmail:
                    for u in spamlist:
                        res = self.imap.uid("COPY", u, "[Gmail]/Trash")
                        self.assertok(res, "uid copy", u, "[Gmail]/Trash")
                # Set deleted flag for spam with high score
                for u in spamdeletelist:
                    if self.gmail is True:
                        res = self.imap.uid("COPY", u, "[Gmail]/Trash")
                        self.assertok(res, "uid copy", u, "[Gmail]/Trash")
                    else:
                        res = self.imap.uid("STORE", u, self.spamflagscmd, "(\\Deleted)")
                        self.assertok(res, "uid store", u, self.spamflagscmd, "(\\Deleted)")
                if self.expunge:
                    self.imap.expunge()

        return (numspam, nummsg, spamdeleted)


    def spamlearn(self):
        learns = [
            {
                'inbox': self.learnspambox,
                'learntype': 'spam',
                'moveto': None
            },
            {
                'inbox': self.learnhambox,
                'learntype': 'ham',
                'moveto': self.movehamto
            },
        ]

        result = []

        for learntype in learns:
            n_learnt = 0
            n_tolearn = 0
            if learntype['inbox']:
                self.logger.debug("Teach {} to SA from: {}".format(learntype['learntype'], learntype['inbox']))
                uidvalidity = self.get_uidvalidity(learntype['inbox'])
                origpastuids = self.pastuid_read(uidvalidity, folder=learntype['learntype'])
                newpastuids = []
                res = self.imap.select(learntype['inbox'])
                self.assertok(res, 'select', learntype['inbox'])
                if self.learnunflagged:
                    typ, uids = self.imap.uid("SEARCH", None, "UNFLAGGED")
                elif self.learnflagged:
                    typ, uids = self.imap.uid("SEARCH", None, "(FLAGGED)")
                else:
                    typ, uids = self.imap.uid("SEARCH", None, "ALL")
                uids = uids[0].split()
                uids = [u for u in uids if int(u) not in origpastuids]
                n_tolearn = len(uids)


                for u in uids:
                    body = self.getmessage(u)
                    # Unwrap spamassassin reports
                    unwrapped = unwrap(BytesIO(body))
                    if unwrapped is not None and len(unwrapped) > 0:
                        body = unwrapped[0]
                    if self.dryrun:
                        out = self.alreadylearnt
                        code = 0
                    else:
                        if os.name == 'nt':
                            p = Popen(["spamc", "--learntype=" + learntype['learntype']], stdin=PIPE, stdout=PIPE)
                        else:
                            p = Popen(["spamc", "--learntype=" + learntype['learntype']], stdin=PIPE, stdout=PIPE, close_fds=True)
                        try:
                            out = p.communicate(body)[0]
                        except:
                            self.logger.exception('spamc error for mail {}'.format(u))
                            self.logger.debug(repr(body))
                            continue
                        code = p.returncode
                        p.stdin.close()
                    if code == 69 or code == 74:
                        errorexit("spamd is misconfigured (use --allow-tell)", self.exitcodeflags)
                    if not out.strip().decode() == self.alreadylearnt:
                        n_learnt += 1
                    newpastuids.append(int(u))
                    self.logger.debug("{} {}".format(u, out))
                    if not self.dryrun:
                        if self.learnthendestroy:
                            if self.gmail:
                                res = self.imap.uid("COPY", u, "[Gmail]/Trash")
                                self.assertok(res, "uid copy", u, "[Gmail]/Trash")
                            else:
                                res = self.imap.uid("STORE", u, self.spamflagscmd, "(\\Deleted)")
                                self.assertok(res, "uid store", u, self.spamflagscmd, "(\\Deleted)")
                        elif learntype['moveto'] is not None:
                            res = self.imap.uid("COPY", u, learntype['moveto'])
                            self.assertok(res, "uid copy", u, learntype['moveto'])
                        elif self.learnthenflag:
                            res = self.imap.uid("STORE", u, self.spamflagscmd, "(\\Flagged)")
                            self.assertok(res, "uid store", u, self.spamflagscmd, "(\\Flagged)")
                self.pastuid_write(uidvalidity, origpastuids, newpastuids, folder=learntype['learntype'])
            result.append((n_tolearn, n_learnt))

        return result

    def do_isbg(self):

        if self.spamc:
            self.satest = ["spamc", "-c"]
            self.sasave = ["spamc"]

        if self.delete and not self.gmail:
            self.spamflags.append("\\Deleted")

        if self.pastuidsfile is None:
            self.pastuidsfile = os.path.expanduser("~" + os.sep + ".isbg-track")
            m = md5()
            m.update(self.imaphost.encode())
            m.update(self.imapuser.encode())
            m.update(repr(self.imapport).encode())
            res = m.hexdigest()
            self.pastuidsfile = self.pastuidsfile + res

        if self.passwdfilename is None:
            m = md5()
            m.update(self.imaphost.encode())
            m.update(self.imapuser.encode())
            m.update(repr(self.imapport).encode())
            self.passwdfilename = os.path.expanduser("~" + os.sep +
                                                     ".isbg-" + m.hexdigest())

        if self.passwordhash is None:
            # We make hash that the password is xor'ed against
            m = md5()
            m.update(self.imaphost.encode())
            m.update(m.digest())
            m.update(self.imapuser.encode())
            m.update(m.digest())
            m.update(repr(self.imapport).encode())
            m.update(m.digest())
            self.passwordhash = m.digest()
            while len(self.passwordhash) < self.passwordhashlen:
                m.update(self.passwordhash)
                self.passwordhash = self.passwordhash + m.digest()

        self.logger.debug("Lock file is {}".format(self.lockfilename))
        self.logger.debug("Trackfile is {}".format(self.pastuidsfile))
        self.logger.debug("SpamFlags are {}".format(self.spamflags))
        self.logger.debug("Password file is {}".format(self.passwdfilename))

        # Acquire lockfilename or exit
        if self.ignorelockfile:
            self.logger.debug("Lock file is ignored. Continue.")
        else:
            if os.path.exists(self.lockfilename) and (os.path.getmtime(self.lockfilename) +
                                                          (self.lockfilegrace * 60) > time.time()):
                self.logger.debug("""\nLock file is present. Guessing isbg
                      is already running. Exit.""")
                errorexit(self.exitcodelocked)
            else:
                lockfile = open(self.lockfilename, 'w')
                lockfile.write(repr(os.getpid()))
                lockfile.close()
                # Make sure to delete lock file
                atexit.register(self.removelock)


        # Figure out the password
        if self.imappasswd is None:
            if self.savepw is False and os.path.exists(self.passwdfilename) is True:
                try:
                    if sys.version_info.major >= 3:
                        self.imappasswd = self.getpw(dehexof(open(self.passwdfilename, "rb").read().decode()), self.passwordhash)
                    else:
                        self.imappasswd = self.getpw(dehexof(open(self.passwdfilename, "rb").read()), self.passwordhash)
                    self.logger.debug("Successfully read password file")
                except:
                    self.logger.exception('Error reading pw!')
                    pass

            # do we have to prompt?
            if self.imappasswd is None:
                if not self.interactive:
                    errorexit("""You need to specify your imap password and save it
                              with the --savepw switch""", self.exitcodeok)
                self.imappasswd = getpass.getpass("IMAP password for %s@%s: "
                                                  % (self.imapuser, self.imaphost))

        # Should we save it?
        if self.savepw:
            f = open(self.passwdfilename, "wb+")
            try:
                os.chmod(self.passwdfilename, 0o600)
            except:
                self.logger.exception('Error saving pw!')
                pass
            if sys.version_info.major >= 3:
                f.write(hexof(self.setpw(self.imappasswd, self.passwordhash)).encode())
            else:
                f.write(hexof(self.setpw(self.imappasswd, self.passwordhash)))
            f.close()


        # Main code starts here

        if self.nossl:
            self.imap = imaplib.IMAP4(self.imaphost, self.imapport)
        else:
            self.imap = imaplib.IMAP4_SSL(self.imaphost, self.imapport)

        # Authenticate (only simple supported)
        res = self.imap.login(self.imapuser, self.imappasswd)
        self.assertok(res, "login", self.imapuser, 'xxxxxxxx')

        # List imap directories
        if self.imaplist:
            imap_list = self.imap.list()
            self.assertok(imap_list, "list")
            if sys.version_info.major >= 3:
                dirlist = str([x.decode() for x in imap_list[1]])
            else:
                dirlist = str(imap_list)
            dirlist = re.sub('\(.*?\)| \".\" \"|\"\', \''," ",dirlist) # string formatting
            self.logger.info(dirlist)

        # Spamassassin training
        learned = self.spamlearn()
        s_tolearn, s_learnt = learned[0]
        h_tolearn, h_learnt = learned[1]

        # Spamassassin processing
        if not self.teachonly:
            numspam, nummsg, spamdeleted = self.spamassassin()

        # sign off
        self.imap.logout()
        del self.imap

        if self.nostats is False:
            if self.learnspambox is not None:
                self.logger.info(("%d/%d spams learnt") % (s_learnt, s_tolearn))
            if self.learnhambox:
                self.logger.info(("%d/%d hams learnt") % (h_learnt, h_tolearn))
            if not self.teachonly:
                self.logger.info(("%d spams found in %d messages") % (numspam, nummsg))
                self.logger.info(("%d/%d was automatically deleted") % (spamdeleted, numspam))

        if self.exitcodes:
            if not self.teachonly:
                res = 0
                if numspam == 0:
                    sys.exit(self.exitcodenewmsgs)
                if numspam == nummsg:
                    sys.exit(self.exitcodenewspam)
                sys.exit(self.exitcodenewmsgspam)

            sys.exit(self.exitcodeok)

def isbg_run():
    isbg = ISBG()
    isbg.parse_args()
    ch = logging.StreamHandler()
    isbg.logger.addHandler(ch)
    if isbg.verbose:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    isbg.do_isbg()

if __name__ == '__main__':
    isbg_run()



