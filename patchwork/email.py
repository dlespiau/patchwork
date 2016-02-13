# Patchwork - automated patch tracking system
# Copyright (C) 2016 Intel Corporation
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

from django.conf import settings
from django.core import mail
from django.template import Context
from django.template.loader import render_to_string


class NotificationEmail(object):
    defaults = {
        'from_email': settings.DEFAULT_FROM_EMAIL,
    }

    def send_email(self, ctx, to_email, **kwargs):
        if not to_email:
            return

        subject_template = ('emails/%s_notification.subject.txt' %
                            self.base_name)
        subject = render_to_string(subject_template, ctx).strip()
        body_template = 'emails/%s_notification.body.txt' % self.base_name
        body = render_to_string(body_template, ctx)

        email = mail.EmailMessage(subject=subject, body=body,
                                  from_email=settings.DEFAULT_FROM_EMAIL,
                                  to=[to_email],
                                  **kwargs)
        email.send()


class ReviewerNotification(NotificationEmail):
    def __init__(self, series, series_url, user, reviewer):
        self.series = series
        self.user = user
        self.reviewer = reviewer
        self.ctx = Context({'series': series,
                            'series_url': series_url,
                            'user': user,
                            'reviewer': reviewer})

    def send(self):
        # do not notify if the reviewer is the same person that has set this
        # field
        if self.user == self.reviewer:
            return
        self.send_email(self.ctx, self.reviewer.email)


class NewReviewerNotification(ReviewerNotification):
    base_name = 'new_reviewer'


class PreviousReviewerNotification(ReviewerNotification):
    base_name = 'previous_reviewer'
