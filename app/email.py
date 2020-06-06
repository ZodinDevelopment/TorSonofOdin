from threading import Thread
import os
from flask import render_template
from flask_mail import Message
from app import app, mail



def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    Thread(target=send_async_email, args=(app, msg)).start()


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(
        '[RyseTor] Reset Your Password',
        sender=app.config['ADMINS'][0],
        recipients=[user.email],
        text_body=render_template(
            'email/reset_password.txt',
            user=user, token=token
        ),
        html_body=render_template(
            'email/reset_password.html',
            user=user, token=token
        )
    )

def indev_registration_email(user, note):
    indev_to_admin(user, note)

    outbox = os.path.join('email', 'outgoing')

    outmsg = os.path.join(outbox, 'registration-{}.txt'.format(user.username))

    with open(outmsg, 'w') as f:
        f.write('subject: "[RyseTor] Registration"')
        f.write('To: {}'.format(user.email))
        text = render_template(
            'email/registration.txt',
            user=user, note=note
        )
        f.write('Body:\n{}'.format(text))
    app.logger.info('New outgoing registration mail at {}'.format(outmsg))
    
    

# def send_registration_email(user, note_to_admin):
    # register_to_admin(user, note_to_admin)

    # send_email(
        # '[RyseTor] Registration',
        # sender=app.config['ADMINS'][0],
        # recipients=[user.email],
        # text_body=render_template(
            # 'email/registration.txt',
            # user=user, note=note_to_admin
        # ),
        # html_body=render_template(
            # 'email/registration.html',
            # user=user, note=note_to_admin
        # )
    # )

def send_registration_email(user, note):

    send_to_admin(user, note)

    send_email(
        '[RyseTor] Registration',
        sender=app.config['ADMINS'][0],
        recipients=[user.email],
        text_body=render_template(
            'email/registration.txt',
            user=user, note=note
        ),
        html_body=render_template(
            'email/registration.html',
            user=user, note=note
        )
    )

# def register_to_admin(user, note_to_admin):

    # send_email(
        # '[RyseTor] New Registration',
        # sender=app.config['ADMINS'][0],
        # recipients=app.config['ADMINS'],
        # text_body=render_template(
            # 'email/new_registration.txt',
            # user=user, note=note_to_admin
        # ),
        # html_body=render_template(
            # 'email/new_registration.html',
            # user=user, note=note_to_admin
        # )
    # )

def indev_to_admin(user, note):
    inbox = os.path.join('email', 'inbox')
    inmail = os.path.join(inbox, 'new-user-{}.txt'.format(user.username))
    text = render_template(
        'email/new_registration.txt',
        user=user, note=note
    )
    with open(inmail, 'w') as f:
        f.write('Subject- "[RyseTor] New Registration"')
        f.write('Body:\n{}'.format(text))
        f.write('Auth Token: {}'.format(user.auth_token))
    app.logger.info('New Admin Mail at {}'.format(inmail))

    

def send_to_admin(user, note):
    send_email(
        '[RyseTor] New Registration',
        sender=app.config['ADMINS'][0],
        recipients=app.config['ADMINS'],
        text_body=render_template(
            'email/new_registration.txt',
            user=user, note=note
        ),
        html_body=render_template(
            'email/new_registration.html',
            user=user, note=note
        )
    )


def indev_approval_email(user, message, admin):

    outbox = os.path.join('email', 'outgoing')
    newmail = os.path.join(outbox, 'approval-{}'.format(user.username))
    text = render_template(
        'email/approval_email.txt',
        user=user, message=message,
        admin=admin
    )
    with open(newmail, 'w') as f:
        f.write('Subject: Approved at RyseTor')
        f.write('To: {}'.format(user.email))
        f.write('Body:\n {}'.format(text))

    app.logger.info("New outgoing mail at {}".format(newmail))


def send_approval_email(user, message, admin):

    send_email(
        '[RyseTor] Registration Approved',
        sender=app.config['ADMINS'][0],
        recipients=[user.email],
        text_body=render_template(
            'email/approval_email.txt',
            user=user, message=message,
            admin=admin
        ),
        html_body=render_template(
            'email/approval_email.html',
            user=user, message=message,
            admin=admin
        )
    )
