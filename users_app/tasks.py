"""
users_app.tasks — Asynchronous email tasks for Videoflix backend

Purpose:
--------
Defines background task(s) used for sending transactional emails
(e.g., confirmation, password reset, notifications) via django-rq.

This function can be enqueued using:
    from django_rq import get_queue
    queue = get_queue("default")
    queue.enqueue(send_email_task, subject, recipients, template, context)
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_email_task(subject, recipient_list, template_name, context):
    """
    Background task for sending HTML-formatted emails.

    Args:
        subject (str): The subject line of the email.
        recipient_list (list[str]): A list of recipient email addresses.
        template_name (str): Path to the Django HTML template.
        context (dict): Context variables to render inside the template.

    Behavior:
        - Renders the given template with the provided context.
        - Sends the email using Django's EmailMultiAlternatives.
        - Falls back to a plain-text message ("Please check your email.") if HTML fails.
    """
    # Render the HTML template with context variables
    html_content = render_to_string(template_name, context)
    from_email = settings.DEFAULT_FROM_EMAIL

    # Construct and attach the email content
    email_message = EmailMultiAlternatives(
        subject,
        "Please check your email.",
        from_email,
        recipient_list,
    )
    email_message.attach_alternative(html_content, "text/html")

    # Attempt to send the email and log any errors
    try:
        email_message.send()
    except Exception as e:
        # Optional: Replace print with proper logging in production
        print(f"Error sending email: {e}")
