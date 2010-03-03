#!/usr/bin/env python

# This Python program scans an IMAP Inbox and runs every
# entry against SpamAssassin. For any entries that match,
# the message is copied to another folder, and the original
# marked or deleted.

# This software was mainly written Roger Binns
# <rogerb@rogerbinns.com> and maintained by Thomas Lecavelier
# <thomas@lecavelier.name> since novembre 2009.
# You may use isbg under any OSI approved open source license
# such as those listed at http://opensource.org/licenses/alphabetical

version="0.99"

from subprocess import Popen, PIPE

import imaplib
import sys
import re
import os
import getpass
import getopt
import string
import socket
import time
import atexit

try:
  from hashlib import md5
except ImportError:
  from md5 import md5

# You can specify your imap password using a command line option (--imappassword).
# This however is a really bad idea since any user on the system can run
# ps and see the command line arguments. If you really must do it non-interactively
# then set the password here.

imapuser=getpass.getuser()
imaphost='localhost'
imapport=0 # autodetect - 143 for standard connection, 993 for imaps
usessl=0
imappassword=None
imapinbox="INBOX"
spaminbox="INBOX.spam"
teachonly=0
learnspambox=None
learnhambox=None
movehamto=None
learnthendestroy=0
interactive=sys.stdin.isatty()
thresholdsize=120000 # messages larger than this aren't considered
pastuidsfile=None
lockfile=None
lockfilename=None
ignorelockfile=0
lockfilegraceminutes=240 
spamc=False
passwordfilename=None # where the password is stored if requested
savepw=0              # save the password
alreadylearnt="Message was already un/learned"

# satest is what command is used test if the message is spam
satest=["spamassassin", "--exit-code"]
# sasave is the one that dumps out a munged message including report
sasave=["spamassassin"]
# what we use to set flags on the original spam in imapbox
spamflagscmd="+FLAGS.SILENT"
# and the flags we set them to (none by default)
spamflags="("
# include the spamassassin report in the message placed in spaminbox
increport=1
# delete messages with a score higher then this
deletehigherthen=0
# expunge before quiting causing all messages marked for deletion
# to actually be deleted
expunge=0
# print imap tracing info
verbose=0
# print stats at end
stats=1
# use different exit codes to show what happened
exitcodes=0

###
### exitcode maps
###

exitcodeok=0         # all went well
exitcodenewmsgs=1    # there were new messages - none of them spam
                     #                         (if exitcodes is on)
exitcodenewspam=2    # they were all spams     (if exitcodes is on)
exitcodenewmsgspam=3 # there were new messages and new spam
                     #                         (if exitcodes is on)
exitcodeflags=10     # there were errors in the command line arguments
exitcodeimap=11      # there was an IMAP level error
exitcodespamc=12     # there was error when communicating between spamc and spamd
                     #
exitcodetty=20       # there was an error because we're not in an interactive tty
exitcodelocked=30    # there's certainly another isbg running

# IMAP implementation detail
# Courier IMAP ignores uid fetches where more than a certain number are listed
# so we break them down into smaller groups of this size
uidfetchbatchsize=25
# password saving stuff. A vague level of obfuscation
passwordhashlen=256 # should be a multiple of 16
passwordhash=None

# Usage message - note that not all options are documented
def usage(ec):
    sslmsg=""
    if hasattr(socket, "ssl"):
        sslmsg="""
  --ssl                 Make an SSL connection to the IMAP server"""
    sys.stderr.write("""isbg: IMAP Spam begone %s

All options are optional (\o/), default are between brackets

  --imaphost hostname   IMAP server name [%s]%s
  --imapuser username   Who you login as [%s]
  --imapinbox mbox      Name of your inbox folder [%s]
  --spaminbox mbox      Name of your spam folder [%s]
  --teachonly           Don't search spam, just learn from folders
  --learnspambox mbox   Name of your learn spam folder [%s]
  --learnhambox mbox    Name of your learn ham folder [%s]
  --movehamto mbox      Move ham to folder [%s]
  --learnthendestroy    Mark learnt messages for deletion
  --maxsize numbytes    Messages larger than this will be ignored as they are
                        unlikely to be spam [%d]
  --noreport            Don't include the SpamAssassin report in the message
                        copied to your spam folder
  --flag                The spams will be flagged in your inbox
  --delete              The spams will be marked for deletion from your inbox
  --deletehigherthen #  Delete any spam with a score higher then #
  --expunge             Cause marked for deletion messages to also be deleted
                        (only useful if --delete is specified)
  --verbose             Show IMAP stuff happening
  --spamc               Use spamc instead of standalone SpamAssassin binary
  --savepw              Store the password to be used in future runs
  --noninteractive      Prevent interactive requests
  --ignorelockfile      Don't stop is lock file is present
  --nostats             Don't print stats
  --exitcodes           Use different exitcodes (see doc)

(Your inbox will remain untouched unless you specify --flag or --delete)

See http://redmine.ookook.fr/projects/isbg/wiki for more details\n""" % (version, imaphost, sslmsg, imapuser, imapinbox, spaminbox, learnspambox, learnhambox, movehamto, thresholdsize))
    sys.exit(ec)

def errorexit(msg, exitcode=exitcodeflags):
    sys.stderr.write(msg)
    sys.stderr.write("\nUse --help to see valid options and arguments\n")
    sys.exit(exitcode)

def addspamflag(flag):
    global spamflags
    if len(spamflags)>1: spamflags=spamflags+" "
    spamflags=spamflags+flag

def hexof(x):
    res=""
    for i in x: res=res+("%02x" % ord(i))
    return res

def hexdigit(c):
    if c>='0' and c<='9':
        return ord(c)-ord('0')
    if c>='a' and c<='f':
        return 10+ord(c)-ord('a')
    if c>='A' and c<='F':
        return 10+ord(c)-ord('A')
    raise ValueError(`c`+"is not a valid hexadecimal digit")

def dehexof(x):
    res=""
    while(len(x)):
        res=res+chr( 16*hexdigit(x[0])+ hexdigit(x[1]))
        x=x[2:]
    return res


# argument processing
longopts=[ "imaphost=", "imapuser=", "imapinbox=", "spaminbox=",
       "maxsize=", "noreport", "flag", "delete", "deletehigherthen=",
       "expunge", "verbose", "trackfile=", "spamc", "ssl", "savepw",
       "nostats", "exitcodes", "learnhambox=", "movehamto=",
       "learnspambox=", "teachonly", "learnthendestroy", "noninteractive",
       "ignorelockfile",
       # options not mentioned in usage
       "imappassword=", "satest=", "sasave=", "spamflagscmd=", "spamflags=",
       "help", "version", "imapport=", "passwordfilename=", "lockfilegraceminutes="
       ]

try:
    opts, pargs=getopt.getopt(sys.argv[1:], None, longopts)
except Exception,e:
    errorexit("option processing failed - "+str(e))

if len(pargs):
    errorexit("unrecognised option(s) - "+`pargs`)

for p in opts:
    if p[0]=="--maxsize":
        try:
            thresholdsize=int(p[1])
        except:
            errorexit("Unrecognized size - "+p[1])
        if thresholdsize<1:
            errorexit("Size "+`thresholdsize`+" is too small")
    elif p[0]=="--deletehigherthen":
        try:
            deletehigherthen=float(p[1])
        except:
            errorexit("Unrecognized score - "+p[1])
        if deletehigherthen<1:
            errorexit("Score "+`deletehigherthen`+" is too small")
    elif p[0]=="--imapport":
        imapport=int(p[1])
    elif p[0]=="--noreport":
        increport=0
    elif p[0]=="--noninteractive":
        interactive=0
    elif p[0]=="--flag":
        addspamflag("\\Flagged")
    elif p[0]=="--delete":
        addspamflag("\\Deleted")
    elif p[0]=="--spamc":
        spamc=True
        satest=["spamc", "-c"]
        sasave=["spamc"]
    elif p[0]=="--expunge":
        expunge=1
    elif p[0]=="--teachonly":
        teachonly=1
    elif p[0]=="--learnthendestroy":
        learnthendestroy=1
    elif p[0]=="--verbose":
        verbose=1
    elif p[0]=="--ssl":
        usessl=1
    elif p[0]=="--savepw":
        savepw=1
    elif p[0]=="--nostats":
        stats=0
    elif p[0]=="--exitcodes":
        exitcodes=1
    elif p[0]=="--help":
        usage(0)
    elif p[0]=="--version":
        print version
        sys.exit(0)
    elif p[0]=="--trackfile":
        pastuidsfile=p[1]
    elif p[0]=="--lockfilename":
        lockfilename=p[1]
    elif p[0]=="--ignorelockfile":
        ignorelockfile=1
    elif p[0]=="--lockfilegraceminutes":
        lockfilegraceminutes = int(p[1])
    else:
        locals()[p[0][2:]]=p[1]

# fixup any arguments

if spamflags[-1]!=')':
    spamflags=spamflags+')'

if imapport==0:
    if usessl: imapport=993
    else:      imapport=143

if pastuidsfile is None:
    pastuidsfile=os.path.expanduser("~"+os.sep+".isbg-track")
    m=md5()
    m.update(imaphost)
    m.update(imapuser)
    m.update(`imapport`)
    res=hexof(m.digest())
    pastuidsfile=pastuidsfile+res

if lockfilename is None:
    lockfilename=os.path.expanduser("~"+os.sep+".isbg-lock")

# Delete lock file
def removelock():
  os.remove(lockfilename)

atexit.register(removelock)

# Password stuff
def getpw(data,hash):
    res=""
    for i in range(0,passwordhashlen):
        c=ord(data[i]) ^ ord(hash[i])
        if c==0:
            break
        res=res+chr(c)
    return res
        
def setpw(pw, hash):
    if len(pw)>passwordhashlen:
        raise ValueError("password of length %d is too long to store (max accepted is %d)" % (len(pw), passwordhashlen))
    res=list(hash)
    for i in range(0, len(pw)):
        res[i]=chr( ord(res[i]) ^ ord(pw[i]) )
    return string.join(res, '')

if passwordfilename is None:
    m=md5()
    m.update(imaphost)
    m.update(imapuser)
    m.update(`imapport`)
    passwordfilename=os.path.expanduser("~"+os.sep+".isbg-"+hexof(m.digest()))

if passwordhash is None:
    # We make hash that the password is xor'ed against
    m=md5()
    m.update(imaphost)
    m.update(m.digest())
    m.update(imapuser)
    m.update(m.digest())
    m.update(`imapport`)
    m.update(m.digest())
    passwordhash=m.digest()
    while len(passwordhash)<passwordhashlen:
        m.update(passwordhash)
        passwordhash=passwordhash+m.digest()

if verbose:
    print "Lock file is", lockfilename
    print "Trackfile is", pastuidsfile
    print "SpamFlags are", spamflags
    print "Password file is", passwordfilename
 
# Acquirelockfilename or exit
if ignorelockfile:
  if verbose:
    print "Lock file is ignored. Continue."
else:
  if os.path.exists(lockfilename) and (os.path.getmtime(lockfilename) + (lockfilegraceminutes * 60) > time.time()):
    if verbose:
      print "\nLock file is present. Guessing isbg is already running. Exit."
    exit(exitcodelocked)
  else:
    lockfile = open(lockfilename, 'w')
    lockfile.write(`os.getpid()`)
    lockfile.close()

# Figure out the password
if imappassword is None:
    if not savepw and os.path.exists(passwordfilename):
        try:
            imappassword=getpw(dehexof(open(passwordfilename, "rb").read()), passwordhash)
            if verbose: print "Successfully read password file"
        except:
            pass
        
    # do we have to prompt?
    if imappassword is None:
        if not interactive:
          errorexit("You need to specify your imap password and save it with the --savepw switch", exitcodeok)
        imappassword=getpass.getpass("IMAP password for %s@%s: " % (imapuser, imaphost))

    # Should we save it?
    if savepw:
        f=open(passwordfilename, "wb+")
        try:
            os.chmod(passwordfilename, 0600)
        except:
            pass
        f.write(hexof(setpw(imappassword, passwordhash)))
        f.close()

# Retrieve the entire message
def getmessage(uid, append_to=None):
    res = imap.uid("FETCH", uid, "(RFC822)")
    assertok(res, 'uid fetch', uid, '(RFC822)')
    if res[0]!="OK":
        assertok(res, 'uid fetch', uid, '(RFC822)')
        try:
            body=res[1][0][1]
        except:
            if verbose:
                print "Confused - rfc822 fetch gave "+`res`
                print "The message was probably deleted while we are running"
            if append_to:
                append_to.append(uid)
    else:
      body=res[1][0][1]
    return body

# This function makes sure that each lines ends in <CR><LF>
# SpamAssassin strips out the <CR> normally
crnlre=re.compile("([^\r])\n", re.DOTALL)
def crnlify(text):
    # we have to do it twice to work right since the re includes
    # the char preceding \n
    return re.sub(crnlre, "\\1\r\n", re.sub(crnlre, "\\1\r\n", text))

# This function checks that the return code is OK
# It also prints out what happened (which would end
# up /dev/null'ed in non-verbose mode)
def assertok(res,*args):
    if verbose:
        print `args`, "=", res
    if res[0]!="OK":
        errorexit("\n%s returned %s - aborting\n" % (`args`, res ), exitcodeimap)

# Main code starts here
if usessl:
    imap=imaplib.IMAP4_SSL(imaphost, imapport)
else:
    imap=imaplib.IMAP4(imaphost,imapport)

# Authenticate (only simple supported)
res=imap.login(imapuser, imappassword)
assertok(res, "login",imapuser, 'xxxxxxxx')

# Spamassassion training
if learnspambox:
  if verbose: print "Teach SPAM to SA from:", learnspambox
  res=imap.select(learnspambox, 0)
  assertok(res, 'select', learnspambox)
  s_tolearn = int(res[1][0])
  s_learnt = 0
  typ, uids = imap.uid("SEARCH", None, "ALL")
  uids = uids[0].split()
  for u in uids:
      body = getmessage(u)
      p=Popen(["spamc", "--learntype=spam"], stdin = PIPE, stdout = PIPE, close_fds = True)
      try:
        out = p.communicate(body)[0]
      except:
        continue
      code = p.returncode
      if code == 69 or code == 74:
        errorexit("spamd is missconfigured (use --allow-tell)")
      p.stdin.close()
      if not out.strip() == alreadylearnt: s_learnt += 1
      if verbose: print u, out
      if learnthendestroy:
        res = imap.uid("STORE", u, spamflagscmd, "(\\Deleted)")
        assertok(res, "uid store", u, spamflagscmd, "(\\Deleted)")
  if expunge:
    imap.expunge()

if learnhambox:
  if verbose: print "Teach HAM to SA from:", learnhambox
  res=imap.select(learnhambox, 0)
  assertok(res, 'select', learnhambox)
  h_tolearn = int(res[1][0])
  h_learnt = 0
  typ, uids = imap.uid("SEARCH", None, "ALL")
  uids = uids[0].split()
  for u in uids:
      body = getmessage(u)
      p=Popen(["spamc", "--learntype=ham"], stdin = PIPE, stdout = PIPE, close_fds = True)
      try:
        out = p.communicate(body)[0]
      except:
        continue
      code = p.returncode
      if code == 69 or code == 74:
        errorexit("spamd is missconfigured (use --allow-tell)")
      p.stdin.close()
      if not out.strip() == alreadylearnt: h_learnt += 1
      if verbose: print u, out
      if movehamto:
        res=imap.uid("COPY", u, movehamto)
        assertok(res, "uid copy", u, movehamto)
      if learnthendestroy or movehamto:
        res = imap.uid("STORE", u, spamflagscmd, "(\\Deleted)")
        assertok(res, "uid store", u, spamflagscmd, "(\\Deleted)")
  if expunge or movehamto:
    imap.expunge()

uids=[]

if not teachonly:
  # check spaminbox exists by examining it
  res=imap.select(spaminbox, 1)
  assertok(res, 'select', spaminbox, 1)

  # select inbox
  res=imap.select(imapinbox, 1)
  assertok(res, 'select', imapinbox, 1)

  # get the uids of all mails with a size less then the thresholdsize
  typ, inboxuids = imap.uid("SEARCH", None, "SMALLER", thresholdsize)
  inboxuids = inboxuids[0].split()

  # pastuids keeps track of which uids we have already seen, so
  # that we don't analyze them multiple times. We store its
  # contents between sessions by saving into a file as Python
  # code (makes loading it here real easy since we just source
  # the file)
  pastuids=[]
  try:
    execfile(pastuidsfile)
  except:
    pass
  # remember what pastuids looked like so that we can compare at the end
  origpastuids=pastuids[:]
  
  # filter away uids that was previously scanned
  uids = [u for u in inboxuids if u not in pastuids]

# Keep track of new spam uids
spamlist=[]

# Keep track of spam that is to be deleted
spamdeletelist=[]

# Main loop that iterates over each new uid we haven't seen before
for u in uids:
    # Retrieve the entire message
    body = getmessage(u, pastuids)

    # Feed it to SpamAssassin in test mode
    p=Popen(satest, stdin=PIPE, stdout=PIPE, close_fds=True)
    try:
      score = p.communicate(body)[0]
      if not spamc:
        m = re.search("score=(-?\d+(?:\.\d+)?) required=(\d+(?:\.\d+)?)", score)
        score = m.group(1) + "/" + m.group(2) + "\n"
    except:
      continue
    if score == "0/0\n":
      errorexit("spamc -> spamd error - aborting", exitcodespamc)

    if verbose: print u, "score:", score

    code = p.returncode
    if code == 0:
        # Message is below threshold
        pastuids.append(u)
    else:
        # Message is spam
        if verbose: print u, "is spam"

        if deletehigherthen and float(score.split('/')[0]) > deletehigherthen:
          spamdeletelist.append(u)
          continue
        
        # do we want to include the spam report
        if increport:
            # filter it through sa
            p = Popen(sasave, stdin = PIPE, stdout = PIPE, close_fds=True)
            try:
              body = p.communicate(body)[0]
            except:
              continue
            p.stdin.close()
            body=crnlify(body)
            res=imap.append(spaminbox, None, None, body)
            # The above will fail on some IMAP servers for various reasons.
            # we print out what happened and continue processing
            if res[0]!='OK':
                print `["append", spaminbox, "{body}"]`, "failed for uid "+`u`+": "+`res`+". Leaving original message alone."
                pastuids.append(u)
                continue
        else:
            # just copy it as is
            res=imap.uid("COPY", u, spaminbox)
            assertok(res, "uid copy", u, spaminbox)

        spamlist.append(u)


nummsg=len(uids)
spamdeleted=len(spamdeletelist)
numspam=len(spamlist)+spamdeleted

# If we found any spams, now go and mark the original messages
if numspam or spamdeleted:
    res=imap.select(imapinbox)
    assertok(res, 'select', imapinbox)
    # Only set message flags if there are any
    if len(spamflags)>2:
        for u in spamlist:
            res=imap.uid("STORE", u, spamflagscmd, spamflags)
            assertok(res, "uid store", u, spamflagscmd, spamflags)
            pastuids.append(u)
    # Set deleted flag for spam with high score
    for u in spamdeletelist:
      res=imap.uid("STORE", u, spamflagscmd, "(\\Deleted)")
      assertok(res, "uid store", u, spamflagscmd, "(\\Deleted)")
    if expunge:
      imap.expunge()

if not teachonly:
  # Now tidy up lists of uids
  newpastuids = list(set([u for u in pastuids if u in inboxuids]))

  # only write out pastuids if it has changed
  if newpastuids!=origpastuids:
      f=open(pastuidsfile, "w+")
      try:
          os.chmod(pastuidsfile, 0600)
      except:
          pass
      f.write("pastuids=")
      f.write(`newpastuids`)
      f.write("\n")
      f.close()

# sign off
imap.logout()
del imap


if stats:
  if learnspambox:
    print "%d/%d spams learnt" % (s_learnt, s_tolearn)
  if learnhambox:
    print "%d/%d hams learnt" % (h_learnt, h_tolearn)
  if not teachonly:
    print "%d spams found in %d messages" % (numspam, nummsg)
    print "%d/%d was automaticaly deleted" % (spamdeleted, numspam)

if exitcodes and nummsg:
    res=0
    if numspam==0:
        sys.exit(exitcodenewmsgs)
    if numspam==nummsg:
        sys.exit(exitcodenewspam)
    sys.exit(exitcodenewmsgspam)

sys.exit(exitcodeok)
