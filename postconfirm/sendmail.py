import os
import smtplib
import syslog
from email.MIMEText import MIMEText

log = syslog.syslog

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
        msg["To"] = "webmaster@" + os.environ.get("SERVER_NAME", "localhost")
        msg["Subject"] = "Failed send: %s" % repr(e)
        msg["X-Orig-Subject"] = subject
        msg["X-Orig-To"] = recipient    
        try:
            server = smtplib.SMTP("localhost")
            server.sendmail(sender, recipient, message)
            server.quit()
        except:
            log(repr(e))
        raise e
