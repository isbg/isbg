#!/usr/bin/python

""" parse an rfc2822 email message and unwrap it if it contains an x-spam-type=original payload """

from email.message import Message
from email.parser import BytesParser
import sys

def unwrap(msg_bytes):
    """ Parse and unwrap message """
    parser = BytesParser()
    msg = parser.parsebytes(msg_bytes)
    if msg.is_multipart():
        parts = []
        pls = msg.get_payload()
        for pl in pls:
            if pl.get_param('x-spam-type', '') == 'original':
                pl_bytes = pl.as_bytes()
                el_idx = pl_bytes.index(b'\n\n')
                parts.append(pl_bytes[el_idx+2:])
        if len(parts) > 0:
            return parts
    return None

if __name__ == '__main__':
    inp = sys.stdin.buffer.read()
    spams = unwrap(inp)
    if spams is not None:
        for spam in spams:
            sys.stdout.buffer.write(spam)
    else:
        sys.stdout.buffer.write(inp)
