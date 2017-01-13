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
    --passwdfilename     Use a file to supply the password
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

try:
    from docopt import docopt  # Creating command-line interface
except ImportError:
    sys.stderr.write("Missing dependency: docopt")

from subprocess import Popen, PIPE

import imaplib
import re
import os
import getpass
import string
import time
import atexit
import json

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

def errorexit(msg, exitcode):
    sys.stderr.write(msg)
    sys.stderr.write("\nUse --help to see valid options and arguments\n")
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
        self.imapuser = ''
        self.imaphost = 'localhost'
        self.imapport = 143
        self.imappasswd = None
        self.imapinbox = "INBOX"
        self.spaminbox = "INBOX.spam"
        self.interactive = sys.stdin.isatty()
        self.maxsize = 120000  # messages larger than this aren't considered
        self.pastuidsfile = None
        self.lockfilegrace = 240
        self.alreadylearnt = "Message was already un/learned"

        # satest is the command that is used to test if the message is spam
        self.satest = ["spamassassin", "--exit-code"]
        # sasave is the one that dumps out a munged message including report
        self.sasave = ["spamassassin"]
        # what we use to set flags on the original spam in imapbox
        self.spamflagscmd = "+FLAGS.SILENT"
        # and the flags we set them to (none by default)
        self.spamflags = []
        # exclude the spamassassin report in the message placed in spaminbox
        self.noreport = False

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
        self.partialrun = None

    def removelock(self):
        os.remove(self.lockfilename)

    # Password stuff
    def getpw(self, data, hash):
        res = ""
        for i in range(0, self.passwordhashlen):
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
        for i in range(0, len(pw)):
            res[i] = chr(ord(res[i]) ^ ord(pw[i]))
        return string.join(res, '')

    # Retrieve the entire message
    def getmessage(self, uid, append_to=None):
        res = self.imap.uid("FETCH", uid, "(RFC822)")
        self.assertok(res, 'uid fetch', uid, '(RFC822)')
        if res[0] != "OK":
            self.assertok(res, 'uid fetch', uid, '(RFC822)')
            try:
                body = res[1][0][1]
            except:
                if self.verbose:
                    print("Confused - rfc822 fetch gave " + repr(res))
                    print("""The message was probably deleted
                          while we were running""")
                if append_to is not None:
                    append_to.append(uid)
        else:
            body = res[1][0][1]
        return body

    # This function checks that the return code is OK
    # It also prints out what happened (which would end
    # up /dev/null'ed in non-verbose mode)
    def assertok(self, res, *args):
        if self.verbose:
            if 'fetch' in args[0] and not self.verbose_mails:
                res = shorten(res, 100)
            print(repr(args), "=", res)
        if res[0] != "OK":
            errorexit("\n%s returned %s - aborting\n"
                      % (repr(args), res), self.exitcodeimap)

    def parse_args(self):
        # Argument processing
        try:
            self.opts = docopt(__doc__, version="isbg version 1.00")
            self.opts = dict([(k,v) for k,v in self.opts.items() if v is not None])
            print(self.opts)
        except Exception, e:
            errorexit("Option processing failed - " + str(e), self.exitcodeflags)


        if self.opts["--delete"] is True:
            if self.opts["--gmail"] is True:
                pass
            else:
                self.spamflags.append("\\Deleted")

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

        if self.opts["--spamc"] is True:
            self.spamc = True
            self.satest = ["spamc", "-c"]
            self.sasave = ["spamc"]

        self.spaminbox = self.opts.get('--spaminbox', self.spaminbox)

        self.lockfilename = self.opts.get('--lockfilename', None)

        self.pastuidsfile = self.opts.get('--trackfile', self.pastuidsfile)

        if self.opts.get("--partialrun") is not None:
            self.partialrun = self.opts["--partialrun"]
            if self.partialrun < 1:
                errorexit("Partial run number must be equal to 1 or higher", self.exitcodeflags)

        self.verbose = self.opts.get('--verbose', False)
        self.verbose_mails = self.opts.get('--verbose-mails', False)
        self.ignorelockfile = self.opts.get("--ignorelockfile", False)
        self.savepw = self.opts.get('--savepw', False)

        self.nossl = self.opts.get('--nossl', False)
        self.imaplist = self.opts.get('--imaplist', False)

        self.learnunflagged = self.opts.get('--learnunflagged', False)
        self.learnthendestroy = self.opts.get('--learnthendestroy', False)
        self.learnthenflag = self.opts.get('--learnthendestroy', False)
        self.expunge = self.opts.get('--expunge', False)

        self.teachonly = self.opts.get('--teachonly', False)

        self.exitcodes = self.opts.get('--exitcodes', False)

        # fixup any arguments

        if self.opts.get("--imapport") is None:
            if self.opts["--nossl"] is True:
                self.imapport = 143
            else:
                self.imapport = 993

        if self.pastuidsfile is None:
            self.pastuidsfile = os.path.expanduser("~" + os.sep + ".isbg-track")
            m = md5()
            m.update(self.imaphost)
            m.update(self.imapuser)
            m.update(repr(self.imapport))
            res = hexof(m.digest())
            self.pastuidsfile = self.pastuidsfile + res

        if self.opts.get("--lockfilename") is None:
            self.lockfilename = os.path.expanduser("~" + os.sep + ".isbg-lock")

    def pastuid_read(self):
        # pastuids keeps track of which uids we have already seen, so
        # that we don't analyze them multiple times. We store its
        # contents between sessions by saving into a file as Python
        # code (makes loading it here real easy since we just source
        # the file)
        self.pastuids = []
        try:
            with open(self.pastuidsfile, 'r') as f:
                self.pastuids = json.load(f)
        except:
            pass

    def pastuid_write(self, newpastuids):
        # Now tidy up lists of uids
        newpastuids = list(set([u for u in self.pastuids if u in inboxuids]))

        # only write out pastuids if it has changed
        if newpastuids != origpastuids:
            f = open(self.pastuidsfile, "w+")
            try:
                os.chmod(self.pastuidsfile, 0600)
            except:
                pass
            json.dump(self.pastuids, f)
            f.close()

    def spamassassin(self):
        uids = []

        # check spaminbox exists by examining it
        res = self.imap.select(self.spaminbox, 1)
        self.assertok(res, 'select', self.spaminbox, 1)

        # select inbox
        res = self.imap.select(self.imapinbox, 1)
        self.assertok(res, 'select', self.imapinbox, 1)

        # get the uids of all mails with a size less then the maxsize
        typ, inboxuids = self.imap.uid("SEARCH", None, "SMALLER", self.maxsize)
        inboxuids = inboxuids[0].split()

        # remember what pastuids looked like so that we can compare at the end
        self.pastuid_read()
        origpastuids = self.pastuids[:]

        # filter away uids that was previously scanned
        uids = [u for u in inboxuids if u not in self.pastuids]

        # Take only X elements if partialrun is enabled
        if self.partialrun is not None:
            uids = uids[:int(self.partialrun)]

        if self.verbose:
            print('Got {} mails to check'.format(len(uids)))

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
            body = self.getmessage(u, self.pastuids)

            # Feed it to SpamAssassin in test mode
            if self.dryrun:
                if processednum > processmax:
                    break
                if processednum < fakespammax:
                    print("Faking spam mail")
                    score = "10/10"
                    code = 1
                else:
                    print("Faking ham mail")
                    score = "0/10"
                    code = 0
                processednum = processednum + 1
            else:
                p = Popen(self.satest, stdin=PIPE, stdout=PIPE, close_fds=True)
                try:
                    score = p.communicate(body)[0]
                    if not self.spamc:
                        m = re.search("score=(-?\d+(?:\.\d+)?) required=(\d+(?:\.\d+)?)",
                                      score)
                        score = m.group(1) + "/" + m.group(2) + "\n"
                    code = p.returncode
                except:
                    continue
            if score == "0/0\n":
                errorexit("spamc -> spamd error - aborting", exitcodespamc)

            if self.verbose:
                print(u, "score:", score)

            if code == 0:
                # Message is below threshold
                # but it was already appended by getmessage...???
                # self.pastuids.append(u)
                pass
            else:
                # Message is spam, delete it or move it to spaminbox (optionally with report)
                if self.verbose:
                    print(u, "is spam")

                if (self.deletehigherthan is not None and
                    float(score.split('/')[0]) > self.deletehigherthan):
                    spamdeletelist.append(u)
                    continue

                # do we want to include the spam report
                if self.noreport is False:
                    if self.dryrun:
                        print("Skipping report because of --dryrun")
                    else:
                        # filter it through sa
                        p = Popen(self.sasave, stdin=PIPE, stdout=PIPE, close_fds=True)
                        try:
                            body = p.communicate(body)[0]
                        except:
                            continue
                        p.stdin.close()
                        body = crnlify(body)
                        res = self.imap.append(self.spaminbox, None, None, body)
                        # The above will fail on some IMAP servers for various reasons.
                        # we print out what happened and continue processing
                        if res[0] != 'OK':
                            print(repr(["append", self.spaminbox, "{body}"]),
                                  "failed for uid" + repr(u) + ": " + repr(res) +
                                  ". Leaving original message alone.")
                            self.pastuids.append(u)
                            continue
                else:
                    if self.dryrun:
                        print("Skipping copy to spambox because of --dryrun")
                    else:
                        # just copy it as is
                        res = self.imap.uid("COPY", u, self.spaminbox)
                        self.assertok(res, "uid copy", u, self.spaminbox)

                spamlist.append(u)


        nummsg = len(uids)
        spamdeleted = len(spamdeletelist)
        numspam = len(spamlist) + spamdeleted

        # If we found any spams, now go and mark the original messages
        if numspam or spamdeleted:
            if self.dryrun:
                print('Skipping labelling/expunging of mails because of --dryrun')
            else:
                res = self.imap.select(self.imapinbox)
                self.assertok(res, 'select', self.imapinbox)
                # Only set message flags if there are any
                if len(spamflags) > 2:
                    for u in spamlist:
                        res = self.imap.uid("STORE", u, self.spamflagscmd, imapflags(self.spamflags))
                        self.assertok(res, "uid store", u, self.spamflagscmd, imapflags(spamflags))
                        self.pastuids.append(u)
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
            if learntype['inbox'] is not None:
                if self.verbose:
                    print("Teach {} to SA from: {}".format(learntype['learntype'], learntype['inbox']))
                res = self.imap.select(learntype['inbox'])
                self.assertok(res, 'select', learntype['inbox'])
                if self.learnunflagged:
                    typ, uids = self.imap.uid("SEARCH", None, "UNFLAGGED")
                else:
                    typ, uids = self.imap.uid("SEARCH", None, "ALL")
                uids = uids[0].split()
                n_tolearn = len(uids)

                for u in uids:
                    body = self.getmessage(u)
                    if self.dryrun:
                        out = self.alreadylearnt
                        code = 0
                    else:
                        p = Popen(["spamc", "--learntype=" + learntype['learntype']],
                                  stdin=PIPE, stdout=PIPE, close_fds=True)
                        try:
                            out = p.communicate(body)[0]
                        except:
                            continue
                        code = p.returncode
                        p.stdin.close()
                    if code == 69 or code == 74:
                        errorexit("spamd is misconfigured (use --allow-tell)", self.exitcodeflags)
                    if not out.strip() == self.alreadylearnt:
                        n_learnt += 1
                    if self.verbose:
                        print(u, out)
                    if not self.dryrun:
                        if self.learnthendestroy:
                            if self.gmail:
                                res = self.imap.uid("COPY", u, "[Gmail]/Trash")
                                self.assertok(res, "uid copy", u, "[Gmail]/Trash")
                            else:
                                res = self.imap.uid("STORE", u, self.spamflagscmd, "(\\Deleted)")
                                self.assertok(res, "uid store", u, self.spamflagscmd, "(\\Deleted)")
                        elif learntype['moveto'] is not None:
                            res = imap.uid("COPY", u, learntype['moveto'])
                            self.assertok(res, "uid copy", u, learntype['moveto'])
                        elif self.learnthenflag:
                            res = imap.uid("STORE", u, self.spamflagscmd, "(\\Flagged)")
                            self.assertok(res, "uid store", u, self.spamflagscmd, "(\\Flagged)")
            result.append((n_tolearn, n_learnt))

        return result

    def do_isbg(self):
        # Make sure to delete lock file
        atexit.register(self.removelock)

        if self.passwdfilename is None:
            m = md5()
            m.update(self.imaphost)
            m.update(self.imapuser)
            m.update(repr(self.imapport))
            self.passwdfilename = os.path.expanduser("~" + os.sep +
                                                ".isbg-" + hexof(m.digest()))

        if self.passwordhash is None:
            # We make hash that the password is xor'ed against
            m = md5()
            m.update(self.imaphost)
            m.update(m.digest())
            m.update(self.imapuser)
            m.update(m.digest())
            m.update(repr(self.imapport))
            m.update(m.digest())
            self.passwordhash = m.digest()
            while len(self.passwordhash) < self.passwordhashlen:
                m.update(self.passwordhash)
                self.passwordhash = self.passwordhash + m.digest()

        if self.verbose:
            print("Lock file is", self.lockfilename)
            print("Trackfile is", self.pastuidsfile)
            print("SpamFlags are", self.spamflags)
            print("Password file is", self.passwdfilename)

        # Acquire lockfilename or exit
        if self.ignorelockfile:
            if self.verbose:
                print("Lock file is ignored. Continue.")
        else:
            if os.path.exists(self.lockfilename) and (os.path.getmtime(self.lockfilename) +
                                                 (self.lockfilegrace * 60) > time.time()):
                if self.verbose:
                    print("""\nLock file is present. Guessing isbg
                          is already running. Exit.""")
                exit(self.exitcodelocked)
            else:
                lockfile = open(self.lockfilename, 'w')
                lockfile.write(repr(os.getpid()))
                lockfile.close()

        # Figure out the password
        if self.imappasswd is None:
            if self.savepw is False and os.path.exists(self.passwdfilename) is True:
                try:
                    self.imappasswd = self.getpw(dehexof(open(self.passwdfilename, "rb").read()),
                                       self.passwordhash)
                    if self.verbose:
                        print("Successfully read password file")
                except:
                    pass

            # do we have to prompt?
            if self.imappasswd is None:
                if not self.interactive:
                    errorexit("""You need to specify your imap password and save it
                              with the --savepw switch""", exitcodeok)
                self.imappasswd = getpass.getpass("IMAP password for %s@%s: "
                                             % (self.imapuser, self.imaphost))

            # Should we save it?
            if self.savepw:
                f = open(self.passwdfilename, "wb+")
                try:
                    os.chmod(self.passwdfilename, 0600)
                except:
                    pass
                f.write(hexof(self.setpw(imappasswd, passwordhash)))
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
            imap_list = str(self.imap.list())
            imap_list = re.sub('\(.*?\)| \".\" \"|\"\', \''," ",imap_list) # string formatting
            print(imap_list)

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
                print("%d/%d spams learnt") % (s_learnt, s_tolearn)
            if self.learnhambox:
                print("%d/%d hams learnt") % (h_learnt, h_tolearn)
            if not self.teachonly:
                print("%d spams found in %d messages") % (numspam, nummsg)
                print("%d/%d was automatically deleted") % (spamdeleted, numspam)

        if self.exitcodes and not self.teachonly:
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
    isbg.do_isbg()

if __name__ == '__main__':
    isbg_run()



