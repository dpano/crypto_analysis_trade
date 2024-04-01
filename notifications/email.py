import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(from_email, to_email, subject, body, smtp_server, port, email_password):
    """
    Send an email using SMTP.
    
    Parameters:
    - from_email: Sender's email address.
    - to_email: Recipient's email address.
    - subject: Email subject.
    - body: Email body.
    - smtp_server: SMTP server address.
    - port: SMTP server port.
    - email_password: Password for sender's email account.
    """
    # Create MIME message
    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    
    # Send email
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()
        server.login(from_email, email_password)
        text = message.as_string()
        server.sendmail(from_email, to_email, text)