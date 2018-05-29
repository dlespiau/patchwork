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

from __future__ import absolute_import

import datetime
from email.encoders import encode_7or8bit
from email.header import Header
from email.mime.nonmultipart import MIMENonMultipart
from email.parser import HeaderParser
import email.utils
import re

from .base import *  # noqa
from patchwork.utils import Order, get_patch_ids, bundle_actions, set_bundle
from patchwork.paginator import Paginator
from patchwork.forms import MultiplePatchForm
from patchwork.models import Comment, Patch
from patchwork.filters import Filters
from patchwork.permissions import Can


def generic_list(request, project, view,
                 view_args={}, filter_settings=[], patches=None,
                 editable_order=False):

    filters = Filters(request)

    params = filters.params()
    for param in ['order', 'page']:
        data = {}
        if request.method == 'GET':
            data = request.GET
        elif request.method == 'POST':
            data = request.POST

        value = data.get(param, None)
        if value:
            params.append((param, value))

    context = {
      'messages': [],
      'project': project,
      'filters': filters,
      'projects': Project.objects.all(),
      'list_view': {'view': view, 'view_params': view_args, 'params': params},
    }

    data = {}
    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST
    order = Order(data.get('order'), editable=editable_order)

    # Explicitly set data to None because request.POST will be an empty dict
    # when the form is not submitted, but passing a non-None data argument to
    # a forms.Form will make it bound and we don't want that to happen unless
    # there's been a form submission.
    if request.method != 'POST':
        data = None
    user = request.user
    properties_form = None
    if user.is_authenticated():

        # we only pass the post data to the MultiplePatchForm if that was
        # the actual form submitted
        data_tmp = None
        if data and data.get('form', '') == 'patchlistform':
            data_tmp = data

        properties_form = MultiplePatchForm(project, data=data_tmp)

    if request.method == 'POST' and data.get('form') == 'patchlistform':
        action = data.get('action', '').lower()

        # special case: the user may have hit enter in the 'create bundle'
        # text field, so if non-empty, assume the create action:
        if data.get('bundle_name', False):
            action = 'create'

        ps = Patch.objects.filter(id__in=get_patch_ids(data))

        if action in bundle_actions:
            errors = set_bundle(user, project, action, data, ps, context)

        elif properties_form and action == properties_form.action:
            errors = process_multiplepatch_form(properties_form, user,
                                                action, ps, context)
        else:
            errors = []

        if errors:
            context['errors'] = errors

    for (filterclass, setting) in filter_settings:
        if isinstance(setting, dict):
            context['filters'].set_status(filterclass, **setting)
        elif isinstance(setting, list):
            context['filters'].set_status(filterclass, *setting)
        else:
            context['filters'].set_status(filterclass, setting)

    if patches is None:
        patches = Patch.objects.filter(project=project)

    # annotate with tag counts
    patches = patches.with_tag_counts(project)

    patches = context['filters'].apply(patches)
    if not editable_order:
        patches = order.apply(patches)

    # we don't need the content or headers for a list; they're text fields
    # that can potentially contain a lot of data
    patches = patches.defer('content', 'headers')

    # but we will need to follow the state and submitter relations for
    # rendering the list template
    patches = patches.select_related('state', 'submitter', 'delegate')

    paginator = Paginator(request, patches)

    context.update({
        'page': paginator.current_page,
        'patchform': properties_form,
        'project': project,
        'order': order,
    })

    return context


def process_multiplepatch_form(form, user, action, patches, context):
    errors = []
    if not form.is_valid() or action != form.action:
        return ['The submitted form data was invalid']

    if len(patches) == 0:
        context['messsages'] += ["No patches selected; nothing updated"]
        return errors

    changed_patches = 0
    for patch in patches:
        if not Can(user).edit(patch):
            errors.append("You don't have permissions to edit patch '%s'"
                          % patch.name)
            continue

        changed_patches += 1
        form.save(patch)

    if changed_patches == 1:
        context['messages'] += ["1 patch updated"]
    elif changed_patches > 1:
        context['messages'] += ["%d patches updated" % changed_patches]
    else:
        context['messages'] += ["No patches updated"]

    return errors


class PatchMbox(MIMENonMultipart):
    patch_charset = 'utf-8'

    def __init__(self, _text):
        MIMENonMultipart.__init__(self, 'text', 'plain',
                                  **{'charset': self.patch_charset})
        self.set_payload(_text.encode(self.patch_charset))
        encode_7or8bit(self)


def get_from(patch, charset):
    if patch.headers:
        headers = HeaderParser().parsestr(patch.headers)
        if 'From' in headers:
            return headers['From']

    # just in case we don't have headers in some old patches
    return email.utils.formataddr(
            (str(Header(patch.submitter.name, charset)),
                patch.submitter.email))


def patch_to_mbox(patch, mbox_options={}):
    postscript_re = re.compile('\n-{2,3} ?\n')

    options = {
        'patch-link': None,
        'request': None,                 # needed to build the link URL
    }
    options.update(mbox_options)

    comment = None
    try:
        comment = Comment.objects.get(patch=patch, msgid=patch.msgid)
    except Exception:
        pass

    body = ''
    if comment:
        body = comment.content.strip() + "\n"

    parts = postscript_re.split(body, 1)
    if len(parts) == 2:
        (body, postscript) = parts
        body = body.strip() + "\n"
        postscript = postscript.rstrip()
    else:
        postscript = ''

    for comment in Comment.objects.filter(patch=patch) \
            .exclude(msgid=patch.msgid):
        body += comment.patch_responses()

    request = options.get('request')
    link_name = options['patch-link']
    if link_name and request:
        body += link_name + ': ' + \
                request.build_absolute_uri(patch.get_absolute_url()) + '\n'

    if postscript:
        body += '---\n' + postscript + '\n'

    if patch.content:
        body += '\n' + patch.content

    delta = patch.date - datetime.datetime.utcfromtimestamp(0)
    utc_timestamp = delta.seconds + delta.days * 24 * 3600

    mail = PatchMbox(body)
    mail['Subject'] = patch.name
    mail['From'] = get_from(patch, mail.patch_charset)
    mail['X-Patchwork-Id'] = str(patch.id)
    if patch.delegate:
        mail['X-Patchwork-Delegate'] = str(patch.delegate.email)
    mail['Message-Id'] = patch.msgid
    mail.set_unixfrom('From patchwork ' + patch.date.ctime())

    copied_headers = ['To', 'Cc', 'Date']
    orig_headers = HeaderParser().parsestr(str(patch.headers))
    for header in copied_headers:
        if header in orig_headers:
            mail[header] = orig_headers[header]

    if 'Date' not in mail:
        mail['Date'] = email.utils.formatdate(utc_timestamp)

    return mail
