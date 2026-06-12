import email
import imaplib
import smtplib
import datetime
import email.mime.multipart
# import config
import base64, multiprocessing, re
from imap_tools import MailBox, AND, OR, NOT


class MunEmail():
    def __init__(self, email, password, imap_server=None):
        # self.imap = imaplib.IMAP4_SSL('outlook.office365.com')
        # self.smtp = smtplib.SMTP('smtp.office365.com')

        self.email = email
        self.password = password
        if not imap_server:
            imap_server = self.get_imap_server(email)
        self.mail_box = MailBox(imap_server)        
        self.list_msg = None
        
    def get_imap_server(self, email):
        print('==get_imap_server==')
        if re.search('@hotmail\.|@live\.|@outlook\.', email, re.IGNORECASE):
            return 'outlook.office365.com'
        if re.search('@gmail\.', email, re.IGNORECASE):
            return 'imap.gmail.com'        
    def login(self, initial_folder='INBOX'):
        try:
            self.mail_box.login(self.email, self.password, initial_folder)
        except:
            return
        else:
            return True
    
    def getEmailUIDS(self):
        return self.mail_box.uids
    
    def getEmailByUIDS(self, uid):
        msg = self.mail_box.fetch(AND(uid=uid))[0]
        return msg
    
    def getEmails(self,limit=0):
        if limit:
            self.list_msg = self.mail_box.fetch(limit=limit, mark_seen=False, reverse=True)
        else:
            self.list_msg = self.mail_box.fetch(AND(all=True), mark_seen=False, reverse=True)
        return self.list_msg      
    
    def sendEmailMIME(self, recipient, subject, message):
        msg = email.mime.multipart.MIMEMultipart()
        msg['to'] = recipient
        msg['from'] = self.username
        msg['subject'] = subject
        msg.add_header('reply-to', self.username)
        # headers = "\r\n".join(["from: " + "sms@kitaklik.com","subject: " + subject,"to: " + recipient,"mime-version: 1.0","content-type: text/html"])
        # content = headers + "\r\n\r\n" + message
        try:
            # self.smtp = smtplib.SMTP(config.smtp_server, config.smtp_port)
            self.smtp.ehlo()
            self.smtp.starttls()
            self.smtp.login(self.username, self.password)
            self.smtp.sendmail(msg['from'], [msg['to']], msg.as_string())
            print("email replied")
        except smtplib.SMTPException:
            print("Error: unable to send email")

    def sendEmail(self, recipient, subject, message):
        headers = "\r\n".join([
            "from: " + self.username,
            "subject: " + subject,
            "to: " + recipient,
            "mime-version: 1.0",
            "content-type: text/html"
        ])
        content = headers + "\r\n\r\n" + message
        attempts = 0
        while True:
            try:
                # self.smtp = smtplib.SMTP(config.smtp_server, config.smtp_port)
                self.smtp.ehlo()
                self.smtp.starttls()
                self.smtp.login(self.username, self.password)
                self.smtp.sendmail(self.username, recipient, content)
                print("   email sent.")
                return
            except Exception as err:
                print("   Sending email failed: %s" % str(err))
                attempts = attempts + 1
                if attempts < 3:
                    continue
                raise Exception("Send failed. Check the recipient email address")

    


def main():
    # email = 'meomun2014@hotmail.com'
    # password = 'Hanoi123!@#'
    # mun_email = MunEmail()
    # mun_email.login(email, password)
    # mun_email.inbox()
    # all_emails = mun_email.allIds()
    # raw_message = mun_email.getEmail(all_emails[1])
    # subject = mun_email.mailSubject()
    # date_ = mun_email.mailDate()
    # from_ = mun_email.mailFrom()
    # # mail_body = mun_email.mailBodyDecoded()
    # mail_content = mun_email.mailContent()
    # print(from_, subject, date_)
    # # print(mail_body)
    # print(mail_content)
    mailbox = MunEmail('meomun2014@hotmail.com', 'Hanoi123!@#')

    mailbox.login('INBOX')
    # list_uids = mailbox.getEmailUIDS()
    # print(list_uids)

    # print(mailbox.uids())
    list_email = mailbox.getEmails(limit=10)
    for msg in list_email:
        print(msg.subject)
        # print(msg.uid)
        # print(msg.date, msg.from_, msg.subject, msg.text.strip())
        # print(msg.flags)
        # break
    
if __name__ == '__main__':
	multiprocessing.freeze_support()
	main()