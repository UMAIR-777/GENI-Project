from email.message  import EmailMessage
from utils.config   import SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD
import smtplib


def send_otp_email(email: str, otp: str) -> bool:
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Your Verification Code'
        msg['From']    = EMAIL_ADDRESS
        msg['To']      = email
        
        html_content = f"""
        <html>
            <body>
                <h1 style=\"color: #2563eb;\">Your OTP Code</h1>
                <p>Your verification code is: <strong>{otp}</strong></p>
                <p>This code will expire in 10 minutes.</p>
            </body>
        </html>
        """
        msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_creds_to_users(email: str, password: str, tenant_name: str) -> bool:
    try:
        msg = EmailMessage()
        msg['Subject'] = f'WelCome To {tenant_name}'
        msg['From']    = EMAIL_ADDRESS
        msg['To']      = email

        html_content = f"""
        <html>
            <body>
                <h1 style=\"color: #2563eb;\">Your OTP Code</h1>
                <p>Your Accounts Credentials: <strong>Email : {email} || Password: {password}</strong></p>
            </body>
        </html>
        """
        msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
