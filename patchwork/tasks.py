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

from __future__ import absolute_import

from celery import task
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User

from patchwork.email import (PreviousReviewerNotification,
                             NewReviewerNotification)
from patchwork.models import Series

logger = get_task_logger(__name__)


@task(name="send_reviewer_notification")
def send_reviewer_notification(series_pk, series_url, user_pk,
                               old_reviewer_pk, new_reviewer_pk):
    series = Series.objects.get(pk=series_pk)
    user = User.objects.get(pk=user_pk)

    logger.info("Sending reviewer notification(s) for series %d" % series_pk)

    if old_reviewer_pk is not None:
        old_reviewer = User.objects.get(pk=old_reviewer_pk)
        email = PreviousReviewerNotification(series, series_url, user,
                                             old_reviewer)
        email.send()
    if new_reviewer_pk is not None:
        new_reviewer = User.objects.get(pk=new_reviewer_pk)
        email = NewReviewerNotification(series, series_url, user, new_reviewer)
        email.send()
