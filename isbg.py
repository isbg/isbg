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

try:
    from hashlib import md5
except ImportError:
    from md5 import md5


imapuser = ''
imaphost = 'localhost'
imappasswd = None
imapinbox = "INBOX"
spaminbox = "INBOX.spam"
interactive = sys.stdin.isatty()
maxsize = 120000  # messages larger than this aren't considered
pastuidsfile = None
lockfilegrace = 240
alreadylearnt = "Message was already un/learned"

# satest is the command that is used to test if the message is spam
satest = ["spamassassin", "--exit-code"]
# sasave is the one that dumps out a munged message including report
sasave = ["spamassassin"]
# what we use to set flags on the original spam in imapbox
spamflagscmd = "+FLAGS.SILENT"
# and the flags we set them to (none by default)
spamflags = "("
# exclude the spamassassin report in the message placed in spaminbox
noreport = False

# ###
# ### exitcode maps
# ###

exitcodeok = 0          # all went well
exitcodenewmsgs = 1     # there were new messages - none of them spam
exitcodenewspam = 2     # they were all spam
exitcodenewmsgspam = 3  # there were new messages and new spam
exitcodeflags = 10      # there were errors in the command line arguments
exitcodeimap = 11       # there was an IMAP level error
exitcodespamc = 12      # error of communication between spamc and spamd
exitcodetty = 20        # error because of non interative terminal
exitcodelocked = 30     # there's certainly another isbg running

# IMAP implementation detail
# Courier IMAP ignores uid fetches where more than a certain number are listed
# so we break them down into smaller groups of this size
uidfetchbatchsize = 25
# password saving stuff. A vague level of obfuscation
passwdfilename = None
passwordhash = None
passwordhashlen = 256  # should be a multiple of 16
partialrun = None


def errorexit(msg, exitcode=exitcodeflags):
    sys.stderr.write(msg)
    sys.stderr.write("\nUse --help to see valid options and arguments\n")
    sys.exit(exitcode)


def addspamflag(flag):
    global spamflags
    if len(spamflags) > 1:
        spamflags = spamflags + " "
    spamflags = spamflags + flag


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


# Argument processing
try:
    opts = docopt(__doc__, version="isbg version 1.00")
except Exception, e:
    errorexit("Option processing failed - " + str(e))

if opts["--delete"] is True:
    if opts["--gmail"] is True:
        pass
    else:
        addspamflag("\\Deleted")

if opts["--deletehigherthan"] is not None:
    try:
        deletehigherthan = float(opts["--deletehigherthan"])
    except:
        errorexit("Unrecognized score - " + opts["--deletehigherthan"])
    if deletehigherthan < 1:
        errorexit("Score " + repr(deletehigherthan) + " is too small")

if opts["--flag"] is True:
    addspamflag("\\Flagged")

if opts["--imaphost"] is not None:
    imaphost = opts["--imaphost"]

if opts["--imappasswd"] is not None:
    imappasswd = opts["--imappasswd"]

if opts["--imapport"] is not None:
    imapport = int(opts["--imapport"])

if opts["--imapuser"] is not None:
    imapuser = opts["--imapuser"]

if opts["--imapinbox"] is not None:
    imapinbox = opts["--imapinbox"]

if opts["--learnspambox"] is not None:
    learnspambox = opts["--learnspambox"]

if opts["--learnhambox"] is not None:
    learnhambox = opts["--learnhambox"]

if opts["--lockfilegrace"] is not None:
    lockfilegrace = int(opts["--lockfilegrace"])

if opts["--maxsize"] is not None:
    try:
        maxsize = int(opts["--maxsize"])
    except:
        errorexit("Unrecognised size - " + opts["--maxsize"])
    if maxsize < 1:
        errorexit("Size " + repr(maxsize) + " is too small")

if opts["--movehamto"] is not None:
    movehamto = opts["--movehamto"]

if opts["--noninteractive"] is True:
    interactive = 0

if opts["--noreport"] is True:
    noreport = True

if opts["--spamc"] is True:
    spamc = True
    satest = ["spamc", "-c"]
    sasave = ["spamc"]

if opts["--spaminbox"] is not None:
    spaminbox = opts["--spaminbox"]

if opts["--lockfilename"] is not None:
    lockfilename = opts["--lockfilename"]

if opts["--trackfile"] is not None:
    pastuidsfile = opts["--trackfile"]

if opts["--partialrun"] is not None:
    partialrun = opts["--partialrun"]
    if partialrun < 1:
        errorexit("Partial run number must be equal to 1 or higher")

# fixup any arguments

if spamflags[-1] != ')':
    spamflags = spamflags + ')'

if opts["--imapport"] is None:
    if opts["--nossl"] is True:
        imapport = 143
    else:
        imapport = 993

if pastuidsfile is None:
    pastuidsfile = os.path.expanduser("~" + os.sep + ".isbg-track")
    m = md5()
    m.update(imaphost)
    m.update(imapuser)
    m.update(repr(imapport))
    res = hexof(m.digest())
    pastuidsfile = pastuidsfile + res

if opts["--lockfilename"] is None:
    lockfilename = os.path.expanduser("~" + os.sep + ".isbg-lock")


# Delete lock file
def removelock():
    os.remove(lockfilename)

atexit.register(removelock)


# Password stuff
def getpw(data, hash):
    res = ""
    for i in range(0, passwordhashlen):
        c = ord(data[i]) ^ ord(hash[i])
        if c == 0:
            break
        res = res + chr(c)
    return res


def setpw(pw, hash):
    if len(pw) > passwordhashlen:
        raise ValueError("""Password of length %d is too long to
                         store (max accepted is %d)"""
                         % (len(pw), passwordhashlen))
    res = list(hash)
    for i in range(0, len(pw)):
        res[i] = chr(ord(res[i]) ^ ord(pw[i]))
    return string.join(res, '')

if passwdfilename is None:
    m = md5()
    m.update(imaphost)
    m.update(imapuser)
    m.update(repr(imapport))
    passwdfilename = os.path.expanduser("~" + os.sep +
                                        ".isbg-" + hexof(m.digest()))

if passwordhash is None:
    # We make hash that the password is xor'ed against
    m = md5()
    m.update(imaphost)
    m.update(m.digest())
    m.update(imapuser)
    m.update(m.digest())
    m.update(repr(imapport))
    m.update(m.digest())
    passwordhash = m.digest()
    while len(passwordhash) < passwordhashlen:
        m.update(passwordhash)
        passwordhash = passwordhash + m.digest()

if opts["--verbose"] is True:
    print("Lock file is", lockfilename)
    print("Trackfile is", pastuidsfile)
    print("SpamFlags are", spamflags)
    print("Password file is", passwdfilename)

# Acquire lockfilename or exit
if opts["--ignorelockfile"] is True:
    if opts["--verbose"] is True:
        print("Lock file is ignored. Continue.")
else:
    if os.path.exists(lockfilename) and (os.path.getmtime(lockfilename) +
                                         (lockfilegrace * 60) > time.time()):
        if opts["--verbose"] is True:
            print("""\nLock file is present. Guessing isbg
                  is already running. Exit.""")
        exit(exitcodelocked)
    else:
        lockfile = open(lockfilename, 'w')
        lockfile.write(repr(os.getpid()))
        lockfile.close()

# Figure out the password
if imappasswd is None:
    if opts["--savepw"] is False and os.path.exists(passwdfilename) is True:
        try:
            imappasswd = getpw(dehexof(open(passwdfilename, "rb").read()),
                               passwordhash)
            if opts["--verbose"] is True:
                print("Successfully read password file")
        except:
            pass

    # do we have to prompt?
    if imappasswd is None:
        if not interactive:
            errorexit("""You need to specify your imap password and save it
                      with the --savepw switch""", exitcodeok)
        imappasswd = getpass.getpass("IMAP password for %s@%s: "
                                     % (imapuser, imaphost))

    # Should we save it?
    if opts["--savepw"] is True:
        f = open(passwdfilename, "wb+")
        try:
            os.chmod(passwdfilename, 0600)
        except:
            pass
        f.write(hexof(setpw(imappasswd, passwordhash)))
        f.close()


# Retrieve the entire message
def getmessage(uid, append_to=None):
    res = imap.uid("FETCH", uid, "(RFC822)")
    assertok(res, 'uid fetch', uid, '(RFC822)')
    if res[0] != "OK":
        assertok(res, 'uid fetch', uid, '(RFC822)')
        try:
            body = res[1][0][1]
        except:
            if opts["--verbose"] is True:
                print("Confused - rfc822 fetch gave " + repr(res))
                print("""The message was probably deleted
                      while we were running""")
            if append_to:
                append_to.append(uid)
    else:
        body = res[1][0][1]
    return body

# This function makes sure that each lines ends in <CR><LF>
# SpamAssassin strips out the <CR> normally
crnlre = re.compile("([^\r])\n", re.DOTALL)


def crnlify(text):
    # we have to do it twice to work right since the re includes
    # the char preceding \n
    return re.sub(crnlre, "\\1\r\n", re.sub(crnlre, "\\1\r\n", text))


# This function checks that the return code is OK
# It also prints out what happened (which would end
# up /dev/null'ed in non-verbose mode)
def assertok(res, *args):
    if opts["--verbose"] is True:
        print(repr(args), "=", res)
    if res[0] != "OK":
        errorexit("\n%s returned %s - aborting\n"
                  % (repr(args), res), exitcodeimap)

# Main code starts here

if opts["--nossl"] is True:
    imap = imaplib.IMAP4(imaphost, imapport)
else:
    imap = imaplib.IMAP4_SSL(imaphost, imapport)

# Authenticate (only simple supported)
res = imap.login(imapuser, imappasswd)
assertok(res, "login", imapuser, 'xxxxxxxx')

# List imap directories
if opts["--imaplist"] is True:
    imap_list = str(imap.list())
    imap_list = re.sub('\(.*?\)| \".\" \"|\"\', \''," ",imap_list) # string formatting
    print(imap_list)

# Spamassassin training
if opts["--learnspambox"] is not None:
    if opts["--verbose"] is True:
        print("Teach SPAM to SA from:", learnspambox)
    res = imap.select(learnspambox, 0)
    assertok(res, 'select', learnspambox)
    s_tolearn = int(res[1][0])
    s_learnt = 0
    typ, uids = imap.uid("SEARCH", None, "ALL")
    uids = uids[0].split()
    for u in uids:
        body = getmessage(u)
        p = Popen(["spamc", "--learntype=spam"],
                  stdin=PIPE, stdout=PIPE, close_fds=True)
        try:
            out = p.communicate(body)[0]
        except:
            continue
        code = p.returncode
        if code == 69 or code == 74:
            errorexit("spamd is misconfigured (use --allow-tell)")
        p.stdin.close()
        if not out.strip() == alreadylearnt:
            s_learnt += 1
        if opts["--verbose"] is True:
            print(u, out)
        if opts["--learnthendestroy"] is True:
            if opts["--gmail"] is True:
                res = imap.uid("COPY", u, "[Gmail]/Trash")
                assertok(res, "uid copy", u, "[Gmail]/Trash")
            else:
                res = imap.uid("STORE", u, spamflagscmd, "(\\Deleted)")
                assertok(res, "uid store", u, spamflagscmd, "(\\Deleted)")
    if opts["--expunge"] is True:
        imap.expunge()

if opts["--learnhambox"] is not None:
    if opts["--verbose"] is True:
        print("Teach HAM to SA from:", learnhambox)
    res = imap.select(learnhambox, 0)
    assertok(res, 'select', learnhambox)
    h_tolearn = int(res[1][0])
    h_learnt = 0
    typ, uids = imap.uid("SEARCH", None, "ALL")
    uids = uids[0].split()
    for u in uids:
        body = getmessage(u)
        p = Popen(["spamc", "--learntype=ham"],
                  stdin=PIPE, stdout=PIPE, close_fds=True)
        try:
            out = p.communicate(body)[0]
        except:
            continue
        code = p.returncode
        if code == 69 or code == 74:
            errorexit("spamd is misconfigured (use --allow-tell)")
        p.stdin.close()
        if not out.strip() == alreadylearnt: h_learnt += 1
        if opts["--verbose"] is True:
            print(u, out)
        if opts["--movehamto"] is not None:
            res = imap.uid("COPY", u, movehamto)
            assertok(res, "uid copy", u, movehamto)
        if opts["--learnthendestroy"] or opts["--movehamto"] is not None:
            res = imap.uid("STORE", u, spamflagscmd, "(\\Deleted)")
            assertok(res, "uid store", u, spamflagscmd, "(\\Deleted)")
    if opts["--expunge"] is True or opts["--movehamto"] is not None:
        imap.expunge()

uids = []

if opts["--teachonly"] is False:
    # check spaminbox exists by examining it
    res = imap.select(spaminbox, 1)
    assertok(res, 'select', spaminbox, 1)

    # select inbox
    res = imap.select(imapinbox, 1)
    assertok(res, 'select', imapinbox, 1)

    # get the uids of all mails with a size less then the maxsize
    typ, inboxuids = imap.uid("SEARCH", None, "SMALLER", maxsize)
    inboxuids = inboxuids[0].split()

    # pastuids keeps track of which uids we have already seen, so
    # that we don't analyze them multiple times. We store its
    # contents between sessions by saving into a file as Python
    # code (makes loading it here real easy since we just source
    # the file)
    pastuids = []
    try:
        execfile(pastuidsfile)
    except:
        pass
    # remember what pastuids looked like so that we can compare at the end
    origpastuids = pastuids[:]

    # filter away uids that was previously scanned
    uids = [u for u in inboxuids if u not in pastuids]

    # Take only X elements if partialrun is enabled
    if partialrun is not None:
        uids = uids[:int(partialrun)]

# Keep track of new spam uids
spamlist = []

# Keep track of spam that is to be deleted
spamdeletelist = []

# Main loop that iterates over each new uid we haven't seen before
for u in uids:
    # Retrieve the entire message
    body = getmessage(u, pastuids)

    # Feed it to SpamAssassin in test mode
    p = Popen(satest, stdin=PIPE, stdout=PIPE, close_fds=True)
    try:
        score = p.communicate(body)[0]
        if opts["--spamc"] is False:
            m = re.search("score=(-?\d+(?:\.\d+)?) required=(\d+(?:\.\d+)?)",
                          score)
            score = m.group(1) + "/" + m.group(2) + "\n"
    except:
        continue
    if score == "0/0\n":
        errorexit("spamc -> spamd error - aborting", exitcodespamc)

    if opts["--verbose"] is True:
        print(u, "score:", score)

    code = p.returncode
    if code == 0:
        # Message is below threshold
        pastuids.append(u)
    else:
        # Message is spam
        if opts["--verbose"] is True:
            print(u, "is spam")

        if (opts["--deletehigherthan"] is not None and
            float(score.split('/')[0]) > deletehigherthan):
            spamdeletelist.append(u)
            continue

        # do we want to include the spam report
        if noreport is False:
            # filter it through sa
            p = Popen(sasave, stdin=PIPE, stdout=PIPE, close_fds=True)
            try:
                body = p.communicate(body)[0]
            except:
                continue
            p.stdin.close()
            body = crnlify(body)
            res = imap.append(spaminbox, None, None, body)
            # The above will fail on some IMAP servers for various reasons.
            # we print out what happened and continue processing
            if res[0] != 'OK':
                print(repr(["append", spaminbox, "{body}"]),
                      "failed for uid" + repr(u) + ": " + repr(res) +
                      ". Leaving original message alone.")
                pastuids.append(u)
                continue
        else:
            # just copy it as is
            res = imap.uid("COPY", u, spaminbox)
            assertok(res, "uid copy", u, spaminbox)

        spamlist.append(u)


nummsg = len(uids)
spamdeleted = len(spamdeletelist)
numspam = len(spamlist) + spamdeleted

# If we found any spams, now go and mark the original messages
if numspam or spamdeleted:
    res = imap.select(imapinbox)
    assertok(res, 'select', imapinbox)
    # Only set message flags if there are any
    if len(spamflags) > 2:
        for u in spamlist:
            res = imap.uid("STORE", u, spamflagscmd, spamflags)
            assertok(res, "uid store", u, spamflagscmd, spamflags)
            pastuids.append(u)
    # If its gmail, and --delete was passed, we actually copy!
    if opts["--delete"] is True and opts["--gmail"] is True:
        for u in spamlist:
            res = imap.uid("COPY", u, "[Gmail]/Trash")
            assertok(res, "uid copy", u, "[Gmail]/Trash")
    # Set deleted flag for spam with high score
    for u in spamdeletelist:
        if opts["--gmail"] is True:
            res = imap.uid("COPY", u, "[Gmail]/Trash")
            assertok(res, "uid copy", u, "[Gmail]/Trash")
        else:
            res = imap.uid("STORE", u, spamflagscmd, "(\\Deleted)")
            assertok(res, "uid store", u, spamflagscmd, "(\\Deleted)")
    if opts["--expunge"] is True:
        imap.expunge()

if opts["--teachonly"] is False:
    # Now tidy up lists of uids
    newpastuids = list(set([u for u in pastuids if u in inboxuids]))

    # only write out pastuids if it has changed
    if newpastuids != origpastuids:
        f = open(pastuidsfile, "w+")
        try:
            os.chmod(pastuidsfile, 0600)
        except:
            pass
        f.write("pastuids=")
        f.write(repr(newpastuids))
        f.write("\n")
        f.close()

# sign off
imap.logout()
del imap


if opts["--nostats"] is False:
    if opts["--learnspambox"] is not None:
        print("%d/%d spams learnt") % (s_learnt, s_tolearn)
    if opts["--learnhambox"] is not None:
        print("%d/%d hams learnt") % (h_learnt, h_tolearn)
    if opts["--teachonly"] is False:
        print("%d spams found in %d messages") % (numspam, nummsg)
        print("%d/%d was automatically deleted") % (spamdeleted, numspam)

if opts["--exitcodes"] is True and nummsg:
    res = 0
    if numspam == 0:
        sys.exit(exitcodenewmsgs)
    if numspam == nummsg:
        sys.exit(exitcodenewspam)
    sys.exit(exitcodenewmsgspam)

sys.exit(exitcodeok)
