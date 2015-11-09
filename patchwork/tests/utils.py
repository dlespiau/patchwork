# Patchwork - automated patch tracking system
# Copyright (C) 2008 Jeremy Kerr <jk@ozlabs.org>
#
# This file is part of the Patchwork package.
#
# Patchwork is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Patchwork is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchwork; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import codecs
from patchwork.models import Project, Person
from patchwork.bin.parsemail import parse_mail
from django.contrib.auth.models import User
from django.forms.fields import EmailField

from email import message_from_file
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid


# helper functions for tests
_test_mail_dir  = os.path.join(os.path.dirname(__file__), 'mail')
_test_patch_dir = os.path.join(os.path.dirname(__file__), 'patches')

class defaults(object):
    project = Project(linkname = 'test-project', name = 'Test Project',
                      listid = 'test.example.com')

    patch_author = 'Patch Author <patch-author@example.com>'
    patch_author_person = Person(name = 'Patch Author',
        email = 'patch-author@example.com')

    comment_author = 'Comment Author <comment-author@example.com>'

    sender = 'Test Author <test-author@example.com>'

    subject = 'Test Subject'

    series_name = 'Test Series'

    series_cover_letter = """This is the test series cover letter.
I hope you'll like it."""

    patch_name = 'Test Patch'

    patch = """--- /dev/null	2011-01-01 00:00:00.000000000 +0800
+++ a	2011-01-01 00:00:00.000000000 +0800
@@ -0,0 +1 @@
+a
"""

    review = """This is a great addition!"""

error_strings = {
    'email': 'Enter a valid email address.',
}

_user_idx = 1
def create_user():
    global _user_idx
    userid = 'test%d' % _user_idx
    email = '%s@example.com' % userid
    _user_idx += 1

    user = User.objects.create_user(userid, email, userid)
    user.save()

    person = Person(email = email, name = userid, user = user)
    person.save()

    return user

def create_maintainer(project):
    user = create_user()
    profile = user.profile
    profile.maintainer_projects.add(project)
    profile.save()
    return user

def find_in_context(context, key):
    if isinstance(context, list):
        for c in context:
            v = find_in_context(c, key)
            if v is not None:
                return v
    else:
        if key in context:
            return context[key]
    return None

def read_patch(filename, encoding = None):
    file_path = os.path.join(_test_patch_dir, filename)
    if encoding is not None:
        f = codecs.open(file_path, encoding = encoding)
    else:
        f = file(file_path)

    return f.read()

def read_mail(filename, project = None):
    file_path = os.path.join(_test_mail_dir, filename)
    mail = message_from_file(open(file_path))
    if 'Message-Id' not in mail:
        mail['Message-Id'] = make_msgid()
    if project is not None:
        mail['List-Id'] = project.listid
    return mail

def create_email(content, subject = None, sender = None, multipart = False,
        project = None, content_encoding = None, in_reply_to = None,
        references = None):
    if subject is None:
        subject = defaults.subject
    if sender is None:
        sender = defaults.sender
    if project is None:
        project = defaults.project
        project.save()
    if content_encoding is None:
        content_encoding = 'us-ascii'

    if multipart:
        msg = MIMEMultipart()
        body = MIMEText(content, _subtype = 'plain',
                        _charset = content_encoding)
        msg.attach(body)
    else:
        msg = MIMEText(content, _charset = content_encoding)

    msg['Message-Id'] = make_msgid()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['List-Id'] = project.listid
    if in_reply_to and references:
        msg['References'] = ' '.join([m.get('Message-Id') for m in references])
        msg['In-Reply-To'] = in_reply_to
    elif references:
        msg['References'] = references
        msg['In-Reply-To'] = references.split()[-1]
    elif in_reply_to:
        msg['References'] = in_reply_to
        msg['In-Reply-To'] = in_reply_to

    return msg

class TestSeries(object):
    def __init__(self, n_patches, has_cover_letter=True):
        if n_patches < 1:
            raise ValueError
        self.n_patches = n_patches
        self.has_cover_letter = has_cover_letter

    def create_cover_letter(self):
        return create_email(defaults.series_cover_letter,
                            subject='[PATCH 0/%d] %s' % (self.n_patches,
                                                         defaults.series_name))

    # in_reply_to: a mail instance
    def create_patch(self, n=0, in_reply_to=None, references=None,
                     subject_prefix='PATCH'):
        in_reply_to_str = None
        if in_reply_to:
            in_reply_to_str = in_reply_to.get('Message-Id')

        if n != 0:
            subject='[%s %d/%d] %s' % (subject_prefix, n,
                                       self.n_patches,
                                       defaults.patch_name)
        else:
            subject='[%s] %s' % (subject_prefix, defaults.patch_name)

        mail = create_email(defaults.patch, subject=subject,
                            in_reply_to=in_reply_to_str, references=references)
        mail['X-Mailer'] = 'git-send-email 2.1.0'
        return mail

    def create_reply(self, mail, references=None):
        if not references:
            references = mail.get('References') or ''
            references += ' ' + mail.get('Message-Id')
        return create_email(defaults.review,
                            subject='Re: ' + mail.get('Subject'),
                            references=references)

    def create_mails(self):
        mails = []
        root_msg = None

        # cover letter
        if self.has_cover_letter:
            cover_letter = self.create_cover_letter()
            mails.append(cover_letter)
            root_msg = cover_letter

        # insert the first patch
        patch = self.create_patch(1, root_msg)
        mails.append(patch)
        if not root_msg:
            root_msg = patch

        # and the remaining patches
        for i in range(2, self.n_patches + 1):
            mails.append(self.create_patch(i, root_msg))

        return mails

    def insert(self, mails=[]):
        if not mails:
            mails = self.create_mails()
        for mail in mails:
            parse_mail(mail)
