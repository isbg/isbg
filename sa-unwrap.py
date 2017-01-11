#!/usr/bin/python

""" parse an rfc2822 email message and unwrap it if it contains an x-spam-type=original payload

    Works on python 2.7+ and 3.x (uses some fairly ugly hacks to do so)

    Does not perfectly preserve whitespace (esp. \r\n vs. \n and \t vs space), also does that
    differently between python 2 and python 3, but this should not impact spam-learning purposes.

"""

from email.message import Message

# import byte parser if it exists (on python 3)
try:
    from email.parser import BytesParser
except ImportError:
    # on python 2, use old parser
    from email.parser import Parser
    BytesParser = Parser
import sys

def unwrap(msg_stream):
    """ Parse and unwrap message """
    parser = BytesParser()
    msg = parser.parse(msg_stream)
    if msg.is_multipart():
        parts = []
        pls = msg.get_payload()
        for pl in pls:
            if pl.get_param('x-spam-type', '') == 'original':
                if hasattr(pl, 'as_bytes'):
                    pl_bytes = pl.as_bytes()
                else:
                    pl_bytes = pl.as_string()
                el_idx = pl_bytes.index(b'\n\n')
                parts.append(pl_bytes[el_idx+2:])
        if len(parts) > 0:
            return parts
    return None

if __name__ == '__main__':
    # select byte streams if they exist (on python 3)
    if hasattr(sys.stdin, 'buffer'):
        inb = sys.stdin.buffer
        outb = sys.stdout.buffer
    else:
        # on python 2 use regular streams
        inb = sys.stdin
        outb = sys.stdout

    spams = unwrap(inb)
    if spams is not None:
        for spam in spams:
            outb.write(spam)
    else:
        outb.write(inp)
