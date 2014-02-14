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
import hmac
import signal
import smtplib
from email.MIMEText import MIMEText

log = syslog.syslog

syslog.openlog("postconfirmd", syslog.LOG_PID | syslog.LOG_USER)
log("Loading '%s' (%s)" % (__name__, __file__))

confirm_fmt = "Confirm: %s:%s:%s"
confirm_pat = "Confirm:[ \t\n\r]+.*:.*:.*"
timestamp_fmt = "%Y-%m-%dT%H:%M:%S"

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
pid  = None
whitelist = set([])
blacklist = set([])
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
                    log(syslog.LOG_ERR, "Invalid regex (not added to whitelist): %s" % (entry))
                    log(syslog.LOG_ERR, e)
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
def read_data():
    global whiteregex
    global blackregex
    
    t1 = time.time()
    try:
        read_whitelist(list(conf.whitelists) + [ conf.confirmlist ])
    except:
        pass

    try:
        whiteregex = read_regexes(list(conf.whiteregex))
    except:
        pass

    try:
        read_blacklist(list(conf.blacklists))
    except:
        pass

    try:
        blackregex = read_regexes(list(conf.blackregex))
    except:
        pass

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

    pid = os.getpid()

    hashkey = filetext(conf.key_file)

    read_data()

    signal.signal(signal.SIGHUP, sighup_handler)


# ------------------------------------------------------------------------------
def sendmail(sender, recipient, subject, text, conf={"smtp_host":"localhost",}, headers={}):

    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    for key in headers:
        msg[key] = headers[key]
    message = msg.as_string()

    try:
        server = smtplib.SMTP(conf["smtp_host"])
        server.sendmail(sender, recipient, message)
        server.quit()
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
    seconds = base64.urlsafe_b64encode(struct.pack(">i",int(time.time()))).strip("=")
    outfd, outfn = tempfile.mkstemp("", seconds, conf.mail_cache_dir)

    text = sys.stdin.read()
    all = True
    out = os.fdopen(outfd, "w+")
    if conf.archive_url_pattern:
        # The following assumes that the 'List-Id' header field has been set
        # properly in the wrapper before sending the message to postconfirmd:
        msg = email.parser.Parser().parsestr(text, headersonly=True)
        if msg['List-Id']:
            list = msg['List-Id'].strip('<>').replace('.ietf.org', '')
            msgid = get_msgid(msg)
            sha = hashlib.sha1(msgid)
            sha.update(list)
            hash = base64.urlsafe_b64encode(sha.digest()).strip("=")
            msg["Archived-At"] = conf.archive_url_pattern % {'list': list, 'hash': hash, "msgid": msgid}
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
def request_confirmation(sender, recipient, cachefn, headers, text):
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

    filename = cachefn.split("/")[-1]

    precedence = headers.get("precedence", "")
    precedence_match = re.search(conf.bulk_regex, precedence)
    if precedence_match:
        log(syslog.LOG_INFO, "Skipped confirmation for 'Precedence: %s' message from <%s>" % (precedence, sender,))
        # leave message in cache till cleaned out
        return 1

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
    msg = headers                       # for the interpolator
    text = str(interpolate.Interpolator(template))

    sendmail(recipient, sender, subject, text, conf)

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

    t1 = time.time()

    for var in ["SENDER", "RECIPIENT" ]:
        if not var in os.environ:
            log(syslog.LOG_ERR, "Environment variable '%s' not set -- can't process input" % (var))
            return 3

    sender  = os.environ["SENDER"].strip()
    sender  = strip_batv(sender)
    recipient=os.environ["RECIPIENT"].strip()

    cachefn, msg, all = cache_mail()

    headers = msg

    err = 0

    precedence = headers.get("Precedence", "")
    precedence_match = re.search(conf.bulk_regex, precedence)
    auto_submitted = headers.get("Auto-Submitted", "")
    auto_submitted_match = re.search(conf.auto_submitted_regex, auto_submitted)

    if (headers.get_content_type() == "multipart/report"
        and ("report-type","delivery-status") in headers.get_params([]) ):
        log(syslog.LOG_INFO, "Received a delivery-status report: %s"  % cachefn)
        err = 1
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
    elif re.search(confirm_pat, headers.get("subject", "")):
        err =  verify_confirmation(sender, recipient, headers)
        if err:
            log(syslog.LOG_INFO, "Message with failed confirmation saved as %s" % (cachefn))
        else:
            os.unlink(cachefn)
    else:
        if   sender.lower() in whitelist or (whiteregex and re.match(whiteregex, sender.lower())):
            err = forward_whitelisted_post(sender, recipient, cachefn, msg, all)
        else:
            err = request_confirmation(sender, recipient, cachefn, headers, msg.get_payload())

    t2 = time.time()
    log(syslog.LOG_INFO, "Wall time in handler: %.6f s." % (t2 - t1))

    if err:
        raise SystemExit(err)

    
