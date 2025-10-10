import smtplib
from email.mime.text import MIMEText

# Define email sender and receiver
sender = 'test@example.com'
receiver = 'user@example.com'

# Email content
message = MIMEText('This is a test email to verify MailSlurper is working.')
message['Subject'] = 'MailSlurper Test'
message['From'] = sender
message['To'] = receiver

# Connect to MailSlurper SMTP server
try:
    smtp_server = smtplib.SMTP('localhost', 1025)
    smtp_server.set_debuglevel(1)
    smtp_server.sendmail(sender, [receiver], message.as_string())
    print("Email sent successfully!")
except Exception as e:
    print(f"Failed to send email: {e}")
finally:
    try:
        smtp_server.quit()
    except:
        pass