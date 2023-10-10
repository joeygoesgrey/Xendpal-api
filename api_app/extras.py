import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from api_app.config import settings
import os
from premailer import Premailer


def send_share_email(email, subject, template_data, template_name="sharetemplate.html"):
    # Set the template folder as an environment variable
    os.environ["TEMPLATE_FOLDER"] = "api_app/templates"

    template_folder = os.environ.get("TEMPLATE_FOLDER")

    # Initialize the Jinja2 environment with the template folder
    env = Environment(loader=FileSystemLoader(template_folder))

    # Get the provided template name
    template = env.get_template(template_name)
    message = template.render(**template_data)

    # Inline CSS styles using Premailer
    premailer = Premailer(message)
    message_with_inline_css = premailer.transform()

    # Create a MIMEMultipart object
    msg = MIMEMultipart("alternative")

    # Set the email content as HTML using MIMEText
    html_part = MIMEText(message_with_inline_css, "html")

    # Attach the HTML part to the MIMEMultipart object
    msg.attach(html_part)

    # Set the Content-Type header to "text/html"
    msg["Content-Type"] = "text/html"

    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_HOST_USER
    msg["To"] = email

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        smtp.send_message(msg)
