# service.py

"""
    Service handler for whitelist lookups, and generation and verification of
    confirmation requests.  Incoming emails are read on stdin, emails from
    whitelisted or confirmed senders are written to stdout.  Emails are cached
    in a cache directory which is expected to be cleaned out regularly by a
    cronjob.
"""

import os
import sys
import tempfile
import syslog

log = syslog.syslog

# ------------------------------------------------------------------------------
# Setup: read initial data before daemonizing.

conf = {}
whitelist = set([])

def setup(configuration, files):
    global conf
    global whitelist

    conf = configuration

    for file in files + list(conf.whitelists):
        if os.path.exists(file):
            sys.stderr.write("Reading %s\n" % file)
            file = open(file)
            whitelist |= set(file.read().split())
            file.close()
    print "Whitelist size: %s" % (len(whitelist))
    print "Initialized."



# ------------------------------------------------------------------------------
# Service handler

def handler():
    """ Lookup email sender in whitelist; forward or cache email pending confirmation.

        It is expected that the following environment variables set:
        SENDER   : Envelope MAIL FROM address
	RECIPIENT: Envelope RCPT TO address
	EXTENSION: The recipient address extension (after the extension
                   separator character in local_part, usually '+' or '-')

        If we know the extension character (and we do, since we only use
        extensions for confirmation mail, and we generate the confirmation
        address extension using the configured extension character) we could
        easily find the extension ourselves.  However, we go with the above
        for compatibility with TMDA.

        The service handler looks up the sender in the whitelist, and if found,
        the mail on stdin is passed out on stdout.  If not found, the mail is
        instead cached in the configured mail cache directory, and a
        confirmation request is sent to the sender address.  If a reply to the
        confirmation mail is received while the original mail is in the cache,
        the original mail is sent out stdout.  It is expected that a cronjob
        cleans out the cache with desired intervals and cache retention time.
    """

    for var in ["SENDER", "RECIPIENT" ]:
        if not var in os.environ:
            log("Environment variable '%s' not set -- can't process input" % (var))
            return 3

    sender  = os.environ["SENDER"]
    recipient=os.environ["RECIPIENT"]

    if sender in whitelist:
        for line in sys.stdin:
            sys.stdout.write(line)
        return 0
    else:
        outfd, outfn = tempfile.mkstemp("", "", conf.mail_cache_dir)
        out = os.fdopen(outfd, "w+")
        for line in sys.stdin:
            out.write(line)
#         out.seek(0)
#         parser = email.parser.Parser()
#         headers = parser.parse(out, headersonly=True)
#         for key in headers.keys():
#             print "%s: %s" % (key, headers[key])
        out.close()
        return 1

