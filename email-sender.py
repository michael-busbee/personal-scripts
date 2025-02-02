import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv(dotenv_path='.env')

# Replace these with your details.
sender_email = os.getenv("GOOGLE_ACCOUNT")
receiver_email = os.getenv("GOOGLE_ACCOUNT")
# Use your 16-character App Password from Google.
app_password = os.getenv("GOOGLE_APP_PASSWORD")

print(os.getcwd())
print(sender_email)
print(app_password)

# Create a multipart message
message = MIMEMultipart("alternative")
message["Subject"] = "Test Email"
message["From"] = sender_email
message["To"] = receiver_email

# Create the plain-text and HTML version of your message.
text = "This is a test email sent via Python using Gmail SMTP server."
html = """
<html>
  <body>
    <p>This is a <b>test email</b> sent via Python using Gmail SMTP server.</p>
  </body>
</html>
"""

# Turn these into MIMEText objects and attach to the message.
part1 = MIMEText(text, "plain")
part2 = MIMEText(html, "html")
message.attach(part1)
message.attach(part2)

# Connect securely to Gmail's SMTP server and send the email.
with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()  # Secure the connection.
    server.login(sender_email, app_password)
    server.sendmail(sender_email, receiver_email, message.as_string())

print("Email sent successfully!")
