# import django_rq
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_email_task(subject, recipient_list, template_name, context):
    """Background task for sending emails."""
    html_content = render_to_string(template_name, context)
    from_email = settings.DEFAULT_FROM_EMAIL

    email_message = EmailMultiAlternatives(
        subject, "Please check your email.", from_email, recipient_list)
    email_message.attach_alternative(html_content, "text/html")

    try:
        email_message.send()
    except Exception as e:
        # Optional: Log the error
        print(f"Error sending email: {e}")
