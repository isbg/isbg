# IMAP Spam Begone

isbg is a script that makes it easy to scan an IMAP inbox for spam using
SpamAssassin and get your spam moved to another folder.

Unlike the normal mode of deployments for SpamAssassin, isbg does 
not need to be involved in mail delivery, and can run on completely 
different machines to where your mailbox actually is. So this is the 
perfect tool to take good care of your ISP mailbox without having to 
leave it.

*   [Features](#Features)
*   [New in 1.00](#New-in-100)
*   [Installation](#Installation)
	*   [Install from source](#Install-from-source)
	*   [Install in Debian](#Install-in-Debian)
*   [Your first run](#Your-first-run)
	*   [SpamAssassin](#SpamAssassin)
		*   [Configure your spamassassin](#Configure-your-spamassassin)
			*   [Allow-tell](#Allow-tell)
*   [CLI Options](#CLI_Options)
*   [Do your first run.](#Do-your-first-run)
*   [Running it](#Running-it)
*   [Your folder names](#Your-folder-names)
*   [How does it work?](#How-does-it-work)
*   [Multiple accounts](#Multiple-accounts)
*   [Saving your password](#Saving-your-password)
*   [SSL](#SSL)
*   [Exit Codes](#Exit-Codes)
*   [Read and Seen flags](#Read-and-Seen-flags)
*   [Gmail Integration](#Gmail-Integration)
*   [Ignored emails](#Ignored-emails)
*   [Partial runs](#Partial-runs)
*   [Contact and about](#Contact-and-about)
*   [License](#License)

# Features<a name="Features"></a>

*   Works with all common IMAP servers
*   Works on Linux, MacOS X and Windows (even smartphones!)
*   Can do IMAP over SSL
*   Can remember your password
*   Will work painlessly against multiple IMAP accounts and servers
*   Is not involved in the mail delivery process, and so can run
on any machine that can contact your IMAP server
*   Highly configurable
*   Sensible defaults so you don't have to do any configuring :-)
*   Compatibility with Python 2.4, 2.5, 2.6
*   Possibility to skip spam detection to stick only to the teach feature
*   Don't fail when meeting horrible and bad formed mail
*   Lock file to prevent multiple instance to run at the same time 
(for cron jobs)

## New in 1.00<a name="New-in-100"></a>

**DEPRECATION NOTICE: if you used the "--ssl" parameter in 0.99, you now
need to stop using it! SSL is now used by default. If you want not to use
it, please use the "--nossl" parameter.**

  * The CLI interface is now implemented with docopt
  * The README now includes the documentation
  * New command --imaplist lists the directories in IMAP account
  * Code now follows PEP-8 style guide
  * Renamed variables to be consistent
  * Added gmail integration (thanks to Orkim!)
  * Added bash scripts for use with multiple accounts
  * SSL is now used by default and "--ssl" parameter is now a "--nossl" parameter
  * New command "--trackfile" now permits trackfile name configuration (thanks naevtamarkus!)
  * New command "--partialrun" now enable isbg to run for only a few emails (thanks naevtamarkus!)

# Installation<a name="Installation"></a>

## Install from source<a name="Install-from-source"></a>

Make sure you have SpamAssassin installed. All the necessary information
can be found on the 
[SpamAssassin wiki](https://wiki.apache.org/spamassassin/FrontPage).

SpamAssassin should be on your $PATH (it installs in `/usr/bin/` by default)

Download isbg.py. You can rename it to anything you want, and make 
it executable (`chmod 555 isbg.py`). It is written in the Python scripting
 language. Python is installed by default on most Linux systems. You can
 can find out more about Python at [www.python.org](http://www.python.org/)

Simply invoke it by whatever name you called the file. For a better experience,
you can add a [bash alias](https://wiki.archlinux.org/index.php/Bash#Aliases)
to your ~/.bashrc file. Here `alias isbg="/path/to/isbg.py"` should do the
trick.

## Install in Debian<a name="Install-in-Debian"></a>

There is a package in mentor.debian.net pending approval from the community.
There should thus be a packaged version soon.

# Your first run<a name="Your-first-run"></a>

## SpamAssassin<a name="SpamAssassin"></a>

If you have never used SpamAssassin before, you'll probably be quite
 nervous about it being too good and taking out legitimate email, or not
 taking out enough spam. It has an easily adustable threshold to change 
how aggressive it is. Run the following command to create your 
preferences file.

<pre>$ spamassassin  &lt;/dev/null &gt;/dev/null
Created user preferences file: /home/rogerb/.spamassassin/user_prefs
</pre>

You can then edit `$HOME/.spamassassin/user_prefs` and change the thresholds.

You can also edit the system-wide settings in `/etc/spamassassin/locals.cf`.

If you want to use the `--learnspambox` or `--learnhambox`, you'll have
 to configure your spamassassin.

### Configure your spamassassin<a name="Configure-your-spamassassin"></a>

If you want to use `--learnspambox` or `--learnhambox` features, 
you have to add this configuration:

#### Allow Tell<a name="Allow-tell"></a>

You have to start `spamd` with the `--allow-tell` option.

On Debian systems (Debian and Ubuntu), you have to edit
 `/etc/default/spamassassin` and replace:

<pre>
OPTIONS="-D --create-prefs --max-children 5 --helper-home-dir" 
</pre>

by:

<pre>
OPTIONS="-D --allow-tell --create-prefs --max-children 5 --helper-home-dir" 
</pre>

Don't forget to restart your spamd server after that
 (`sudo service spamassassin restart` on Debian).


## CLI Options<a name="CLI_Options"></a>

The default behaviour of isbg is to not make any changes your Inbox 
unless you specify specific command line options. Consequently you can 
experiment without worry at the begining.

Your first step is to create a new folder to receive suspected spam.
 I use one named 'spam'.

Run isbg with the `--help` option to see what options are available:

<pre>
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
    --nostats            Don't print stat
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
</pre>

You can specify your imap password using `--imappasswd`.
This however is a really bad idea since any user on the system can run `ps` and
 see the command line arguments. If you really must do it non-interactively
 then set the password here.


## Do your first run.<a name="Do-your-first-run"></a>

<pre>
$ isbg.py --imaphost mail.example.com  --savepw
IMAP password for rogerb@mail.example.com:
</pre>

The amount of time it takes will be proportional to the size of your
 inbox. You can specify `--verbose` if you want to see the gory details of
 what is going on.

You can now examine your spam folder and will see what spam was 
detected. You can change the SpamAssassin threshold in your `user_prefs` 
file it created earlier.

isbg remembers which messages it has already seen, so that it 
doesn't process them again every time it is run. If you are testing and 
do want it to run again, then remove the trackfile (default 
`$HOME/.isbg-track*`).

If you specified `--savepw` then isbg will remember your password the 
next time you run against the same server with the same username. You 
should not specify `--savepw` in future runs unless you want to change the
 saved password.

# Running it<a name="Running-it"></a>

You'll probably want something to actually be done with the original
 spams in your inbox. By default nothing happens to them, but you have 
two options available. If you specify `--flag` then spams will be flagged.

You can get the messages marked for deletion by specifying `--delete`.
 If you never want to see them in your inbox, also specify the `--expunge`
 option after `--delete` and they will be removed when isbg logs out of 
the IMAP server.

# Your folder names<a name="Your-folder-names"></a>

Each IMAP implementation names their folders differently, and most 
IMAP clients manage to hide most of this from you. If your IMAP server 
is Courier, then your folders are all below INBOX, and use dots to 
seperate the components.

The UWash server typically has the folders below Mail and uses
slash (`/`) to seperate components.

If you don't know how your IMAP folders are implemented, you can always use
the `--imaplist` option to find out.

# How does it work?<a name="How-does-it-work"></a>

IMAP assigns each message in a folder a unique id. isbg scans the 
folder for messages it hasn't seen before, and for each one, downloads 
the message and feeds it to SpamAssassin. If SpamAssassin says the 
message is spam, then the SpamAssassin report is uploaded into your spam
 folder. Unless you specify the `--noreport` option, in which case the 
message is copied from your Inbox to the Spam folder (the copy happens on
 the IMAP server itself so this option is good if you are on a low 
bandwidth connection).

# Multiple accounts<a name="Multiple-accounts"></a>

By default isbg saves the list of seen IMAP message unique IDs in a 
file in your home directory. It is named `.isbg-trackXXXX` where XXXX is a
 16 byte identifier based on the IMAP host, username and port number. 
Consequently you can just run isbg against different servers/accounts 
and it will automatically keep the tracked UIDs seperate. You can 
override the filename with `--trackfile`.

To run isbg for multiple accounts one after another, it is possible to use 
bash scripts like the ones in the folder "bash_scripts". Since these scripts
contain passwords and are thus sensitive data, make sure the file permissions
are very restrictive.

# Saving your password<a name="Saving-your-password"></a>

If you don't want isbg to prompt you for your password each time, 
you can specify the `--savepw` option. This will save the password in a 
file in your home directory. The file is named `.isbg-XXXX` where XXXX is a
 16 byte identifier based on the IMAP host, username and port number 
(the same as for the multiple accounts description above). You can 
override the filename with `--passwdfilename`.

The password is obfuscated, so anyone just looking at the contents 
won't be able to see what it is. However, if they study the code to isbg
 then they will be able to figure out how to de-obfuscate it, and 
recover the original password. (isbg needs the original password each 
time it is run as well).

Consequently you should regard this as providing minimal protection if
 someone can read the file.

# SSL<a name="SSL"></a>

isbg can do IMAP over SSL if your version of Python has been 
compiled with SSL support. Since Python 2.6, SSL comes built in with Python.

However you should be aware that the SSL support does NOT check the 
certificate name nor validate the issuer. If an attacker can intercept 
the connection and modify all the packets flowing by, then they will be 
able to pose as the IMAP server. Other than that, the connection will 
have the usual security features of SSL.

# Exit Codes<a name="Exit-Codes"></a>

When ISBG exits, it uses the exit code to tell you what happened. In
 general it is zero if all went well, and non-zero if there was a 
problem. You can turn on additional reporting by using the `--exitcodes` 
command line option.

|code| `--exitcodes` needed| description|
|:--:|:-------------------:|:----------:|
|0 |  no    |All went well|
|1 |  yes   |There was at least one new message, and none of them were spam|
|2 |  yes   |There was at least one new message, and all them were spam|
|3 |  yes   |There were new messages, with at least one spam and one non-spam|
|10|  no    |There were errors in the command line arguments|
|11|  no    |The IMAP server reported an error|
|12|  no    |There was an error of communication between spamc and spamd|
|20|  no    |The program was not launched in an interactive terminal|
|30|  no    |There is another instance of `isbg` running|

# Read and Seen flags<a name="Read-and-Seen-flags"></a>

There are two flags IMAP uses to mark messages, Recent and Seen. 
Recent is sent to the first IMAP client that connects after a new 
message is received. Other clients or subsequent connections won't see 
that flag. The Seen flag is used to mark a message as read. IMAP clients
 explicitly set Seen when a message is being read.

Pine and some other mailers use the Recent flag to mark new mail. 
Unfortunately this means that if isbg or any other IMAP client has even 
looked at the Inbox, the messages won't be shown as new. It really 
should be using Seen.

The IMAP specification does not permit clients to change the Recent flag.a

# Gmail Integration<a name="Gmail-Integration"></a>

Gmail has a few unique ways that they interact with a mail client. isbg must
be considered to be a client due to interacting with the Gmail servers over
IMAP, and thus, should conform to these special requirements for propper
integration.

There are two types of deletion on a Gmail server.

**Type 1: Move a message to '[Gmail]/Trash' folder.**

This "removes all labels" from the message. It will no longer appear in any
folders and there will be a single copy located in the trash folder.
Gmail will "empty the trash" after the received email message is 30 days old.

You can also do a "Normal IMAP delete" on the message in the trash folder to
cause it to be removed permanently without waiting 30 days.

**Type 2: Normal IMAP delete flag applied to a message.**

This will "remove a single label" from a message. It will no longer appear
in the folder it was removed from but will remain in other folders and also
in the "All Mail" folder.

Enable Gmail integration mode by passing `--gmail` in conjunction with
`--delete` on the command line when invoking isbg. These are the features
which are tweaked:

- The `--delete` command line switch will be modified so that it will result in
  a Type 1 delete.

- The `--deletehigherthan` command line switch will be modified so that it will
  results in a Type 1 delete.

- If `--learnspambox` is used along with the `--learnthendestroy` option, then a
  Type 1 delete occurs leaving only a copy of the spam in the Trash.

- If `--learnhambox` is used along with the `--learnthendestroy` option, then a
  Type 2 delete occurs, only removing the single label.

Reference information was taken from
[here](https://support.google.com/mail/answer/78755?hl=en)

# Ignored emails<a name="Ignored-emails"></a>

By default, isbg ignores emails that are bigger than 120000 bytes since spam
are not often that big. If you ever get emails with score of 0 on 5 (0.0/5.0),
 it is likely that SpamAssassin is skipping it due to size.

Defaut maximum size can be changed with the use of the `--maxsize` option.

# Partial runs<a name="Partial-runs"></a>

By default, isbg scans the whole inbox folder. If you want to restrict the number
of emails that are scanned, you can use the `--partialrun` option specifying the 
number of unseen (not scanned before) emails you want to check.

This may be useful when your inbox has a lot of emails, since deletion and mail
tracking are only performed at the end of the run and full scans can take too
long.

# Contact and about<a name="Contact-and-about"></a>

This software was written by Roger Binns 
&lt;[rogerb@rogerbinns.com](mailto:rogerb@rogerbinns.com)&gt;
 and is maintained by Thomas Lecavelier 
&lt;[thomas@lecavelier.name](mailto:thomas@lecavelier.name)&gt;
 since november 2009.
With the great help of Anders Jenbo since v0.99.

# License<a name="License"></a>

As said by Roger Binns when he hang over isbg to Thomas Lecavelier: 
 " You may use isbg under any OSI approved open source license such as 
those listed at [http://opensource.org/licenses/alphabetical](http://opensource.org/licenses/alphabetical) "
