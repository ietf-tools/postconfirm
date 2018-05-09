# service.py

""" The handler which constitute the actual service.

    Provides whitelist lookups, and generation and verification of
    confirmation requests.  Incoming emails are read on stdin, emails from
    whitelisted or confirmed senders are written to stdout.  Emails are cached
    in a cache directory which is expected to be cleaned out regularly by a
    cronjob.

"""

import os
import re
import sys
import time
import tempfile
import syslog
import base64
import hashlib
import struct
import interpolate
import email
import email.parser
import email.utils
import hmac
import signal
import smtplib
import urllib
import dns.resolver
import dns.rdatatype

from email.MIMEText import MIMEText

#from flufl import bounce
#from datetime import datetime as Datetime, timedelta as Timedelta

log = syslog.syslog

syslog.openlog("postconfirmd", syslog.LOG_PID | syslog.LOG_USER)
log("Loading '%s' (%s)" % (__name__, __file__))

confirm_fmt = "Confirm: %s:%s:%s"
confirm_pat = "Confirm:[ \t\n\r]+.*:.*:.*"
timestamp_fmt = "%Y-%m-%dT%H:%M:%S"

def err(msg):
    sys.stderr.write("Error: %s\n" % (msg, ))
    log(syslog.LOG_ERR, msg)

def debug(expr, locals):
    msg = '%s: %s' % (expr, eval(expr, globals(), locals))
    log(syslog.LOG_INFO, msg)

# ------------------------------------------------------------------------------
def filetext(file):
    if os.path.exists(file):
        file = open(file)
        text = file.read()
        file.close
        return text
    else:
        return ""
        
# ------------------------------------------------------------------------------
# Setup: read initial data before daemonizing.

conf = {}
listinfo = {}
pid  = None
whitelist = set([])
blacklist = set([])
#bouncelist = {}
whiteregex = None
blackregex = None
hashkey  = None

# ------------------------------------------------------------------------------
def read_whitelist(files):
    global whitelist

    whitelist = set([])
    for file in files:
        if os.path.exists(file):
            file = open(file)
            entries = set(file.read().lower().split())
            whitelist |= entries
            file.close()
            log("Read %s whitelist entries from %s\n" % (len(entries), file.name))
    log("Whitelist size: %s" % (len(whitelist)))

# ------------------------------------------------------------------------------
def read_regexes(files):

    regexlist = []
    for file in files:
        if os.path.exists(file):
            file = open(file)
            entries = file.read().split()
            file.close()
            for entry in entries:
                try:
                    re.compile(entry)
                except Exception, e:
                    err("Invalid regex (not added to whitelist): %s\n  Exception: %s" % (entry, e))
                else:
                    if not entry in regexlist:
                        regexlist.append(entry)
            log("Read %s regexlist entries from %s\n" % (len(entries), file.name))
    log("Regexlist size: %s" % (len(regexlist)))
    if regexlist:
        regex = "^(%s)$" % "|".join(regexlist)
    else:
        regex = ""        
    return regex

# ------------------------------------------------------------------------------
def read_blacklist(files):
    global blacklist

    blacklist = set([])
    for file in files:
        if os.path.exists(file):
            file = open(file)
            entries = set(file.read().lower().split())
            blacklist |= entries
            file.close()
            log("Read %s blacklist entries from %s\n" % (len(entries), file.name))
    log("Blacklist size: %s" % (len(blacklist)))

# ------------------------------------------------------------------------------
def read_listinfo():
    global listinfo

    listinfo = {}
    try:
        from Mailman import Utils
        from Mailman import MailList
        for name in Utils.list_names():
            mmlist = MailList.MailList(name, lock=False)
            listinfo[name] = {}
            listinfo[name]['archive'] = bool(mmlist.archive)
        log("Read %s mailman listinfo entries" % len(listinfo))
    except Exception as e:
        log("Exception when reading mailman listinfo: %s" % e)

# ------------------------------------------------------------------------------
# def read_bouncelist(file):
#     global bouncelist
# 
#     if os.path.exists(file):
#         with open(file) as file:
#             entries = file.read().splitlines()
#             tuples = [ e.split(None, 1) for e in entries ]
#             bouncelist = dict([ (a,Datetime.strptime(t, timestamp_fmt)) for t,a in tuples ])
#         log("Read %s bouncelist entries from %s\n" % (len(entries), file.name))
#     log("Bouncelist size: %s" % (len(bouncelist)))

# ------------------------------------------------------------------------------
# def write_bouncelist(bouncelist):
#     cutoff = Datetime.now() - Timedelta(hours=conf.remember_bounce_hours)
#     with open(conf.bouncelist, "w") as file:
#         for a, t in bouncelist.items():
#             if t > cutoff:
#                 file.write("%s %s\n" % (t.strftime(timestamp_fmt), a))

# ------------------------------------------------------------------------------
# def update_bouncelist(addresses):
#     global bouncelist
# 
#     t = Datetime.now()
#     for a in addresses:
#         bouncelist[a.lower()] = t
#     write_bouncelist(bouncelist)
#     # Tell root daemon process to re-read the data files
#     os.kill(pid, signal.SIGHUP)

# ------------------------------------------------------------------------------
def read_data():
    global whiteregex
    global blackregex
    global listinfo
    
    t1 = time.time()
    try:
        read_whitelist(list(conf.whitelists) + [ conf.confirmlist ])
    except Exception as e:
        log("IOError: %s" % e)

    try:
        whiteregex = read_regexes(list(conf.whiteregex))
    except Exception as e:
        log("IOError: %s" % e)

    try:
        read_blacklist(list(conf.blacklists))
    except Exception as e:
        log("IOError: %s" % e)

    try:
        blackregex = read_regexes(list(conf.blackregex))
    except Exception as e:
        log("IOError: %s" % e)

    try:
        read_listinfo()
    except Exception as e:
        log("IOError: %s" % e)

#     try:
#         read_bouncelist(conf.bouncelist)
#     except Exception as e:
#         log("IOError: %s" % e)


    t2 = time.time()
    log(syslog.LOG_INFO, "Wall time for reading data: %.6f s." % (t2 - t1))    

# ------------------------------------------------------------------------------
def sighup_handler(signum, frame):
    """Re-read our data files"""
    read_data()

# ------------------------------------------------------------------------------
def setup(configuration, files):
    global conf
    global pid
    global hashkey

    conf = configuration
    if "mailman_dir" in conf:
        sys.path.append(conf["mailman_dir"])

    pid = os.getpid()

    hashkey = filetext(conf.key_file)

    read_data()

    signal.signal(signal.SIGHUP, sighup_handler)


# ------------------------------------------------------------------------------
def send_smtp(fromaddr, toaddrs, msg, host, port):
    try:
        server = smtplib.SMTP(host, port)
        #server.set_debuglevel(1)    
        server.sendmail(fromaddr, toaddrs, msg)
        #log("SMTP %s:%s  %s -> %s" % (host, port, fromaddr, toaddrs))
        server.quit()
    except Exception as e:
        log(syslog.LOG_ERR, "Error sending mail: %s" % (e, ))
        raise

# ------------------------------------------------------------------------------
def sendmail(sender, recipients, subject, text, host='localhost', port=25, headers={}):

    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipients
    for key in headers:
        msg[key] = headers[key]
    message = msg.as_string()

    try:
        send_smtp(sender, recipients, message, host, port)
        #log("Sent mail from '%s' to '%s' about '%s'" % (sender, recipient, subject))
        return True
    except Exception, e:
        log(repr(e))

# ------------------------------------------------------------------------------
def get_msgid(msg):
    msgid = msg['Message-Id']
    if not msgid:
        msgid = msg['Resent-Message-Id']
    if msgid:
        msgid = msgid.strip('<>')
    else:
        msgid = email.utils.make_msgid('ARCHIVE')
    return msgid


# ------------------------------------------------------------------------------
def cache_mail():
    global listinfo

    seconds = base64.urlsafe_b64encode(struct.pack(">i",int(time.time()))).strip("=")
    outfd, outfn = tempfile.mkstemp("", seconds, conf.mail_cache_dir)

    text = sys.stdin.read()
    all = True
    out = os.fdopen(outfd, "w+")
    msg = email.message_from_string(text)
    if conf.archive_url_pattern:
        # The following assumes that the 'List-Id' header field has been set
        # properly in the wrapper before sending the message to postconfirmd:
        if msg['List-Id']:
            from Mailman import MailList # This has to happen after we're configured
            try:
                list = re.search('<([^>]+)>', msg['List-Id']).group(1).replace('.ietf.org', '')
            except Exception:
                list = msg['List-Id'].strip('<>').replace('.ietf.org', '')
            if not list in listinfo:
                try:
                    mmlist = MailList.MailList(list, lock=False)
                    log("Mailman list archive setting for %s: %s" % (list, mmlist.archive))
                except Exception as e:
                    mmlist = None
                    log("No mailman info for list %s: %s" % (list, e))
                listinfo[list] = {}
                listinfo[list]['archive'] = mmlist != None and bool(mmlist.archive)
            if listinfo[list]['archive']:
                msgid = get_msgid(msg)
                sha = hashlib.sha1(msgid)
                sha.update(list)
                hash = base64.urlsafe_b64encode(sha.digest()).strip("=")
                msg["Archived-At"] = conf.archive_url_pattern % {'list': list, 'hash': hash, "msgid": msgid}
                log("Setting Archived-At: %s" % msg["Archived-At"])
            else:
                log("Listinfo[%s]['archive'] = %s" % (list, listinfo[list]['archive']))
        out.write(msg.as_string(unixfrom=True))
    else:
        msg = text
        out.write(text)
    out.close()
    return outfn, msg, all


# ------------------------------------------------------------------------------
def hash(bytes):
    return base64.urlsafe_b64encode(hmac.new(hashkey, bytes, hashlib.sha224).digest()).strip("=")

# ------------------------------------------------------------------------------
def make_hash(sender, recipient, filename):
    return hash( "%s-%s-%s" % (sender, recipient, filename, ) )

# ------------------------------------------------------------------------------
def pad(bytes):
    "Pad with '=' till the string is a multiple of 4"
    return bytes + "=" * ((4 - len(bytes) % 4 ) % 4)

# ------------------------------------------------------------------------------
def request_confirmation(sender, recipient, cachefn, msg):
    """Generate a confirmation request, and send it to the poster for confirmation.

    The request subject line contains:
        'Confirm: <recipient>-<date>-<cachefn>-<hash>'
        Hash is calculated over:
        '<key><sender>-<recipient>-<cachefn><key>'

        <sender> is cleartext
        <recipient> is cleartext
        <cachefn> is the tempfile.mkstmp basename
        <key> is binary
    """
    #log('request_confirmation(%s, %s, %s, ...)' % (sender, recipient, cachefn, ))
    filename = cachefn.split("/")[-1]

    precedence = msg.get("precedence", "")
    precedence_match = re.search(conf.bulk_regex, precedence)
    if precedence_match:
        log(syslog.LOG_INFO, "Skipped confirmation for 'Precedence: %s' message from <%s>" % (precedence, sender,))
        # leave message in cache till cleaned out
        return 1

    body = msg.get_payload()
    while isinstance(body, list):
        body = body[0].get_payload()
    text = body
    confirm_match = re.search(confirm_pat, text)
    if confirm_match:
        dummy, rcp, fn, hash = confirm_match.group(0).rsplit(":", 3)
        if valid_hash(sender, rcp.lstrip(), fn, hash):
            # We have a valid confirmation code inside a message which did
            # not have a confirmation code in the subject line.  It's very
            # likely that this means it's a non-delivery message for an
            # earlier confirmation request.  Don't send a confirmation
            # message for this message, but leave it in cache for possible
            # manual handling
            log(syslog.LOG_INFO, "Skipped confirmation for auto-reply, body contained valid '%s'" % (confirm_match.group(0),))
            return 1

    if sender.lower() in set([ "", recipient.lower() ]):
        log(syslog.LOG_INFO, "Skipped requesting confirmation from <%s>" % (sender,))
        os.unlink(cachefn)
        return 1

    if sender.lower() in blacklist or (blackregex and re.match(blackregex, sender.lower())):
        log(syslog.LOG_INFO, "Skipped confirmation from blacklisted <%s>" % (sender,))
        os.unlink(cachefn)
        return 1

#     if sender.lower() in bouncelist:
#         cutoff = Datetime.now() - Timedelta(hours=conf.remember_bounce_hours)        
#         bouncetime = bouncelist[sender.lower()]
#         if bouncetime > cutoff:
#             log(syslog.LOG_INFO, "Skipped confirmation from bouncing <%s>" % (sender,))
#             os.unlink(cachefn)
#             return 1
#         else:
#             update_bouncelist([])
            
    hash_output = make_hash(sender, recipient, filename)

    log(syslog.LOG_INFO, "Requesting confirmation: <%s> to %s, '%s', %s" % (sender, recipient, filename, hash_output))

    #print "Hash input: %s" % (hash_input, )
    #print "Hash output: %s" % (hash_output, )

    # The ':' is a convenient separator character as it's not permitted in
    # email addresses, and it's not used in our base64 alphabet.  It also
    # conveniently will lets us separate out the Confirm: part at the same
    # time as we split the interesting stuff into parts.
    subject = confirm_fmt % (recipient, filename, hash_output)

    template = filetext(conf.mail_template)
    text = interpolate.interpolate(template, {'filename':filename, 'sender':sender, 'recipient':recipient, 'msg':msg, 'conf':conf})

    sendmail(recipient, sender, subject, text, conf.confirm.smtp.host, conf.confirm.smtp.port)

    return 1
    

# ------------------------------------------------------------------------------
def verify_confirmation(sender, recipient, msg):
    log(syslog.LOG_DEBUG, "Verifying confirmation from <%s> to %s" % (sender, recipient))
    
    subject = msg.get("subject", "")
    subject = re.sub("\s", "", subject)
    dummy, recipient, filename, hash = subject.rsplit(":", 3)

    # Require the sender to be somebody
    if sender == "":
        return 1

    # Require the sender to be different from the recipient
    if sender == recipient:
        return 1

    if not valid_hash(sender, recipient, filename, hash):
        return 1

    # We have a valid confirmation -- update the whitelist and the
    # confirmation file
    if sender.lower() in whitelist:
        log(syslog.LOG_INFO, "Already in whitelist: <%s>" % (sender, ))
    else:
        log(syslog.LOG_INFO, "Adding <%s> to whitelist" % (sender, ))
        whitelist.add(sender)
        file = open(conf.confirmlist, "a")
        file.write("%s\n" % sender)
        file.close()

        # Tell root daemon process to re-read the data files
        os.kill(pid, signal.SIGHUP)

    # Output the cached message and delete the cache file
    log(syslog.LOG_INFO, "Forwarding cached message from <%s> to %s" % (sender, recipient, ))
    cachefn = os.path.join(conf.mail_cache_dir, filename)
    forward_cached_post(cachefn)

    return 0

# ------------------------------------------------------------------------------
def valid_hash(sender, recipient, filename, hash):

    # Require a corresponding message in the cache:
    cachefn = os.path.join(conf.mail_cache_dir, filename)
    if not os.path.exists(cachefn):
        log(syslog.LOG_WARNING, "No cached message for confirmation '%s'" % (filename))
        return False

    # Require that the hash matches
    good_hash = make_hash(sender, recipient, filename)
    if not good_hash == hash:
        log(syslog.LOG_WARNING, "Received hash didn't match -- make_hash(<%s>, '%s', '%s') -> %s != %s" % (sender, recipient, filename, good_hash, hash))
        return False

    return True

# ------------------------------------------------------------------------------
def forward_cached_post(cachefn):
    file = open(cachefn)
    while True:
        text = file.read(8192)
        if not text:
            break
        sys.stdout.write(text)
    file.close()
    os.unlink(cachefn)

# ------------------------------------------------------------------------------
def forward_whitelisted_post(sender, recipient, cachefn, msg, all):
    log(syslog.LOG_DEBUG, "Forwarding from whitelisted <%s> to %s" % (sender, recipient))
    if all:
        sys.stdout.write(msg.as_string())
    else:
        forward_cached_post(cachefn)
    return 0

# ------------------------------------------------------------------------------
def strip_batv(sender):
    if "=" in sender and re.search("^[A-Za-z0-9-]+=[A-Za-z0-9-]+=[^=]+@", sender):
        log(syslog.LOG_INFO, "Stripping BATV prefix from local part of '%s'" % (sender))
        return re.sub("^[A-Za-z0-9-]+=[A-Za-z0-9-]+=", "", sender)
    else:
        return sender

# ------------------------------------------------------------------------------
def parse_options():
    import argparse
    import textwrap

    help = """
    NAME
      postconfirm - Mail confirmation system

    ...  postconfirmd [options]

    DESCRIPTION

      postconfirm consists of postconfirmd, which is the long-running
      (daemon) part, and postconfirmc, which is the client part of a
      client-server program which handles email confirmations. It is
      intended as a front-end to mailing lists. It provides
      funcitonality which is a subset of TMDA, but is adapted to
      high-volume usage and does not have anywhere near all the bells
      and whistles which TMDA has. On the other hand, since the
      whitelist lookup is done by the long-running server part, the
      overhead of doing a verification that a poster has a confirmed
      address is much smaller than for TMDA.

      Early tests indicate that with a whitelist of 16000 entries a lookup
      costs about 0.01 seconds and about ~5 Mbytes for the server daemon, in
      contrast whith TMDA which cost between ~10s and ~600s and ~98 Mb *per
      lookup* as it was set up in front of the IETF lists.

    ACTIONS
      confirm (the default action):

      Somewhat simplified, the flow for regular mail is as follows:

         mail agent
             |
             v
         postconfirm/mailman wrapper [copy] -> cached in cache dir
             |
             v
         postconfirmc <==> postconfirmd
             |
             v
         postconfirm/mailman wrapper [white] -> Mailman
           [grey]
             |
             v
         (waiting for confirmation)

      In the start of the flow above, a message comes in. If the envelope
      From is in the lists known by postconfirmd, it is passed through the
      mailman/ postconfirm wrapper, where postconfirmc is called to talk
      with postconfirmd and get either an OK to pass the message to Mailman,
      or cache it.

      In more detail, this is the sequence of actions that postconfirm goes
      through when processing an incoming email message:

      1. The mail is put in the cache directory.

      2. If the message is a delivery-status report (content-type
         multipart/report, report-type delivery-status) then this is logged,
         and no further action is taken.

      3. If the precedence matches the bulk_regex setting in the
         configuration file, then:

         a. if the envelope sender is in the whitelist or the white_regex
             list, then the message is forwarded directly.

         b. if not, the receipt of a bulk message is logged, and no further
             action is taken.

      4. If the message has an auto-submitted header, and the value matches
         the auto_submitted_regex in the configuration file, then:

         a. if the envelope sender is in the whitelist or the white_regex
            list, then the message is forwarded directly.

         b. if not, the receipt of a bulk message is logged, and no further
            action is taken.

      5. If the subject matches the regex for postconfirm's confirmation
         email subject, the confirmation is processed, and then:

         a. if the confirmation is valid, the held message is forwarded,
            and the confirmed address is added to the whitelist.

         b. if not, the failed confirmation is logged, and the message
            is saved.

      6. If the envelope sender is in the whitelist or the white_regex list,
         the message is forwarded.

      7. If there was no match earlier, a confirmation request is sent out
         for the message.

      dmarc-rewrite:

      For use with mailing lists, aliases, etc., where the presence of
      strict dmarc rules will prevent acceptance of the list messages
      unless rewriting is done.

      dmarc-reverse:

      The inverse operation of dmarc-rewrite. Undoes the rewrite, 
      and replaces the rewritten address with the original address.

            
    OPTIONS...

    FILES
      postconfirmd reads its configuration from the following files (if
      found), in the given order:

          <bin-dir>/postconfirm.conf
          /etc/postconfirm.conf
          /etc/postconfirm/postconfirm.conf
          ~/.postconfirmrc

      where <bin-dir> is the directory where postconfirmd is installed.

    AUTHOR
      Written by Henrik Levkowetz, <henrik@merlot.tools.ietf.org>. Uses the
      daemonize module from Chad J. Schroeder, from the Python Cookbook at
      http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731, and
      the readyexec module from Frank J. Tobin, available at
      http://readyexec.sourceforge.net/.

    COPYRIGHT
      Copyright 2008-2017 Henrik Levkowetz

      This program is free software; you can redistribute it and/or modify
      it under the terms of the GNU General Public License as published by
      the Free Software Foundation; either version 2 of the License, or (at
      your option) any later version. There is NO WARRANTY; not even the
      implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
      PURPOSE. See the GNU General Public License for more details.

    """
    _prolog, _middle, _epilog = textwrap.dedent(help.expandtabs()).split('...', 2)

    class HelpFormatter(argparse.RawDescriptionHelpFormatter):
        def _format_usage(self, usage, actions, groups, prefix):
            if prefix is None or prefix == 'usage: ':
                prefix = 'SYNOPSIS\n  '
            return _prolog+super(HelpFormatter, self)._format_usage(usage, actions, groups, prefix)

    parser = argparse.ArgumentParser("postconfirmc", description=_middle, epilog=_epilog,
                                     formatter_class=HelpFormatter, add_help=False)

    group = parser.add_argument_group(argparse.SUPPRESS)

    group.add_argument('action', metavar='{ confirm | dmarc-rewrite | dmarc-reverse }',
                                                        help="the action to take")
    group.add_argument('-h', '--help', action='help',   help="show this help message and exit")
    group.add_argument('--stop', action='store_true',   help="stop the postconfirmd daemon")
    group.add_argument('--socket', metavar='SOCKET',    help="use the given SOCKET for client-daemon communication")
    group.add_argument('-f', '--sender',                help="the envelope sender address")
    group.add_argument('-e', '--echo', action='store_true',
                                                        help="just echo back the command line")
    group.add_argument('recipient', nargs='*',          help="recipients, used with dmarc-rewrite and dmarc-reverse commands")

    options = parser.parse_args()

    return options

# ------------------------------------------------------------------------------

def confirm(sender, recipient):
    """ Lookup email sender in whitelist; forward or cache email pending confirmation.

        It is expected that the following environment variables set:
        SENDER   : Envelope MAIL FROM address
	RECIPIENT: Envelope RCPT TO address

        The service handler looks up the sender in the whitelist, and if found,
        the mail on stdin is passed out on stdout.  If not found, the mail is
        instead cached in the configured mail cache directory, and a
        confirmation request is sent to the sender address.  If a reply to the
        confirmation mail is received while the original mail is in the cache,
        the original mail is sent out stdout.  It is expected that a cronjob
        cleans out the cache with desired intervals and cache retention time.
    """

    cachefn, msg, all = cache_mail()

    err = 0
    # With a return code of 0, the incoming message will be forwarded
    # With a return code of 1, the incoming message will be left in cache until it's cleared out.
    # All other return codes indicate postconfirmd failures, and the message will be passed through

    precedence = msg.get("Precedence", "")
    precedence_match = re.search(conf.bulk_regex, precedence)
    auto_submitted = msg.get("Auto-Submitted", "")
    auto_submitted_match = re.search(conf.auto_submitted_regex, auto_submitted)
#    bounced_addresses = bounce.scan_message(msg)

    if (msg.get_content_type() == "multipart/report"
        and ("report-type","delivery-status") in msg.get_params([]) ):
        log(syslog.LOG_INFO, "Received a delivery-status report: %s"  % cachefn)
        err = 1
#     elif bounced_addresses:
#         log(syslog.LOG_INFO, "Received permanent failure delivery status for: %s" % (str(bounced_addresses),))
#         update_bouncelist(bounced_addresses)
#         err = 1
    elif precedence_match:
        if   sender.lower() in whitelist or (whiteregex and re.match(whiteregex, sender.lower())):
            err = forward_whitelisted_post(sender, recipient, cachefn, msg, all)
        else:
            log(syslog.LOG_INFO, "Skipped confirmation for %s message from <%s>" % (precedence, sender,))
            err = 1
        # return code for "don't forward"
        # leaves message in cache till cleaned out        
    elif auto_submitted_match:
        if   sender.lower() in whitelist or (whiteregex and re.match(whiteregex, sender.lower())):
            err = forward_whitelisted_post(sender, recipient, cachefn, msg, all)
        else:
            log(syslog.LOG_INFO, "Skipped confirmation for %s message from <%s>" % (auto_submitted, sender,))
            err = 1
    elif re.search(confirm_pat, msg.get("subject", "")):
        err =  verify_confirmation(sender, recipient, msg)
        if err:
            log(syslog.LOG_INFO, "Message with failed confirmation saved as %s" % (cachefn))
        else:
            os.unlink(cachefn)
    else:
        if   sender.lower() in whitelist or (whiteregex and re.match(whiteregex, sender.lower())):
            err = forward_whitelisted_post(sender, recipient, cachefn, msg, all)
        else:
            err = request_confirmation(sender, recipient, cachefn, msg)

    if err:
        raise SystemExit(err)

# ----------------------------------------------------------------------
# DMARC related
#----------------------------------------------------------------------

def get_dns_record(dom, rtype):
    resolver = dns.resolver.Resolver()
    resolver.lifetime = conf.dmarc.resolver.lifetime
    resolver.timeout = conf.dmarc.resolver.timeout
    try:
        recs = resolver.query(dom, rtype)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return None
    except dns.exception.DNSException as error:
        log('DNSException: Unable to resolve %s: %s', dom, error.__doc__)
        return None
    return recs


def dmarc_reject_or_quarantine(domain, org=False):
    # This takes a domain and a flag stating whether
    # we should check the organizational domains.  It returns one of three
    # values:
    # * True if the DMARC policy is reject or quarantine;
    # * False if is not;
    # * A special sentinel if we should continue looking
    dmarc_domain = '_dmarc.%s'%domain
    policy = None
    rrecs = get_dns_record(dmarc_domain, dns.rdatatype.TXT)
    if rrecs == None:
        return False
    # Be as robust as possible in parsing the result.
    results_by_name = {}
    cnames = {}
    # Check all the records returned by DNS.  Keep track of the CNAMEs for
    # checking later on.  Ignore any other non-TXT records.
    for rec in rrecs.response.answer:
        if rec.rdtype == dns.rdatatype.CNAME:
            cnames[rec.name.to_text()] = (rec.items[0].target.to_text())
        if rec.rdtype != dns.rdatatype.TXT:
            continue
        result = ''.join([ record for record in rec.items[0].strings ])
        name = rec.name.to_text()
        results_by_name.setdefault(name, []).append(result)
    #
    want_names = set([dmarc_domain + '.'])
    expands = list(want_names)
    seen = set(expands)
    while expands:
        item = expands.pop(0)
        if item in cnames:
            if cnames[item] in seen:
                # CNAME loop.
                continue
            expands.append(cnames[item])
            seen.add(cnames[item])
            want_names.add(cnames[item])
            want_names.discard(item)
    assert len(want_names) == 1, ('Error in CNAME processing for %s; want_names != 1.'%(dmarc_domain,))
    for name in want_names:
        if name not in results_by_name:
            continue
        dmarcs = [ record for record in results_by_name[name] if record.startswith('v=DMARC1;') ]
        if len(dmarcs) == 0:
            sys.stderr.write("no DMARC1 records for %s\n" % (dmarc_domain, ))
            return None
        if len(dmarcs) > 1:
            log('RRset of TXT records for %s has %d v=DMARC1 entries; ignoring them per RFC 7489, Section 6.6.3 .' %
                (dmarc_domain, len(dmarcs)))
            return None
        for entry in dmarcs:
            match = re.search(r'\bsp=(\w*)\b', entry, re.IGNORECASE)
            if org and match:
                policy = match.group(1).lower()
            else:
                match = re.search(r'\bp=(\w*)\b', entry, re.IGNORECASE)
                if match:
                    policy = match.group(1).lower()
                else:
                    continue
            if policy in ('reject', 'quarantine'):
                return True
    return False
    

def quote(s):
    return urllib.quote(s).replace('%', conf.dmarc.rewrite.quote_char)

def unquote(q):
    return urllib.unquote(q.replace(conf.dmarc.rewrite.quote_char, '%'))

def dmarc_rewrite(sender, recipients):
    text = sys.stdin.read()
    rewrite_done = False
    msg = email.message_from_string(text)
    if conf.dmarc.rewrite.require and conf.dmarc.rewrite.require.header:
        for key in conf.dmarc.rewrite.require.header:
            if msg[key] in conf.dmarc.rewrite.require.header[key]:
                break
        else:
            send_smtp(sender, recipients, text, conf.dmarc.rewrite.smtp.host, conf.dmarc.rewrite.smtp.port)
            #log("No dmarc rewrite requirement matched for %s -> %s" % (sender, recipients))
            return
    from_field = msg["From"]
    from_name, from_addr = email.utils.parseaddr(from_field)
    if from_addr:
        from_local, at, from_dom = from_addr.partition('@')
        if at == '@' and dmarc_reject_or_quarantine(from_dom):
            new_addr = '%s@%s' % (quote(from_addr), conf.dmarc.domain)
            new_from = email.utils.formataddr((from_name, new_addr))
            # do rewrite
            msg['X-Original-From'] = msg['From']
            del msg['From']
            msg['From'] = new_from
            rewrite_done = True

    if rewrite_done:
        send_smtp(sender, recipients, msg.as_string(), conf.dmarc.rewrite.smtp.host, conf.dmarc.rewrite.smtp.port)
        log("Dmarc rewrite: '%s' to '%s' --> %s" % (from_field, new_from, recipients))
    else:
        send_smtp(sender, recipients, text, conf.dmarc.rewrite.smtp.host, conf.dmarc.rewrite.smtp.port)
        #log("No dmarc rewrite done for '%s' --> %s" % (sender, recipients))

# ------------------------------------------------------------------------------

def dmarc_reverse(sender, recipient):
    recipients = []

    text = sys.stdin.read()
    msg = email.message_from_string(text)
    if sender.lower() in whitelist or (whiteregex and re.match(whiteregex, sender.lower())):
        for field in [ 'To', 'Cc', ]:
            addresses = msg.get_all(field)
            if addresses:
                reversed = []
                dirty = False
                for name, addr in email.utils.getaddresses(addresses):
                    oaddr = addr
                    if addr.endswith('@%s'%conf.dmarc.domain):
                        localpart, dom  = addr.rsplit('@', 1)
                        addr = unquote(localpart)
                        recipients.append( email.utils.formataddr((name, addr)) )
                        dirty = True
                        log("dmarc-reverse message-id=%s from=<%s> x-original-to=<%s> to=<%s>" % (msg['message-id'], sender, oaddr, addr, ))
                    reversed.append( email.utils.formataddr((name, addr)) )
                if dirty:
                    del msg[field]
                    for a in reversed:
                        msg[field] = a
        send_smtp(sender, recipients, msg.as_string(), conf.dmarc.reverse.smtp.host, conf.dmarc.reverse.smtp.port)
        return 0
    else:
        log("Received a dmarc-rewrite message from a sender not in whitelist or confirmed list: %s" % sender)
        return 4


# ------------------------------------------------------------------------------
# Service handler

def handler():
    try:
        options = parse_options()

        if options.echo:
            log('sys.argv: %s' % sys.argv)

        if not options.sender:
            if "SENDER" in os.environ:
                options.sender = os.environ["SENDER"]
            else:
                log(syslog.LOG_ERR, "sender not provided -- can't process input")
                return 3

        if not options.recipient:
            if "RECIPIENT" in os.environ:
                options.recipient = os.environ["RECIPIENT"]
            else:
                log(syslog.LOG_ERR, "recipient not provided -- can't process input")
                return 3

        t1 = time.time()

        sender    = strip_batv(options.sender)
        recipient = options.recipient
        if isinstance(recipient, list):
            if options.action != 'dmarc-rewrite':
                if len(recipient) > 1:
                    log(syslog.LOG_ERR, "Only the dmarc-rewrite action accepts multiple recipients: %s" % recipients)
                recipient = recipient[0].strip()
            else:
                recipient = [ r.strip() for r in recipient ]
        else:
            if options.action == 'dmarc-rewrite':
                recipient = [ recipient.strip() ]
            else:
                recipient = recipient.strip()

        if   options.action == 'confirm':
            result = confirm(sender, recipient)
        elif options.action == 'dmarc-rewrite':
            result = dmarc_rewrite(sender, recipient)
        elif options.action == 'dmarc-reverse':
            result = dmarc_reverse(sender, recipient)
        else:
            log(syslog.LOG_ERR, "Bad command: %s" % (options.action, ))
            result = 3

        t2 = time.time()
        log(syslog.LOG_INFO, "Wall time in %s handler: %.6f s." % (options.action, t2 - t1))

        return result

    except Exception as e:
        sys.stderr.write("Exception: %s\n" % e)
        raise
        return 2
