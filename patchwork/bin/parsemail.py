#!/usr/bin/env python
#
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

import argparse
import codecs
import datetime
from email import message_from_file
from email.header import Header, decode_header
from email.parser import HeaderParser
from email.utils import parsedate_tz, mktime_tz
from fnmatch import fnmatch
from functools import reduce
import logging
import operator
import re
import sys
import weakref

import django
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q
from django.utils.log import AdminEmailHandler
from django.utils import six
from django.utils.six.moves import map

from patchwork import lock as lockmod
from patchwork.lock import release
from patchwork.models import (Patch, Project, Person, Comment, State, Series,
                              SeriesRevision, SeriesRevisionPatch,
                              DelegationRule, get_default_initial_patch_state,
                              series_revision_complete, SERIES_DEFAULT_NAME)
from patchwork.parser import parse_patch, patch_get_filenames

LOGGER = logging.getLogger(__name__)

VERBOSITY_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

list_id_headers = ['List-ID', 'X-Mailing-List', 'X-list']
whitespace_re = re.compile(r'\s+')


def normalise_space(str):
    return whitespace_re.sub(' ', str).strip()


def clean_header(header):
    """ Decode (possibly non-ascii) headers """

    def decode(fragment):
        (frag_str, frag_encoding) = fragment
        if frag_encoding:
            return frag_str.decode(frag_encoding)
        elif isinstance(frag_str, six.binary_type):  # python 2
            return frag_str.decode()
        return frag_str

    fragments = list(map(decode, decode_header(header)))

    return normalise_space(u' '.join(fragments))


def find_project(mail):
    project = None
    listid_res = [re.compile(r'.*<([^>]+)>.*', re.S),
                  re.compile(r'^([\S]+)$', re.S)]

    for header in list_id_headers:
        if header in mail:

            for listid_re in listid_res:
                match = listid_re.match(mail.get(header))
                if match:
                    break

            if not match:
                continue

            listid = match.group(1)

            # order_by will put projects with a blank subject_prefix_tags
            # first
            projects = Project.objects.filter(listid=listid).\
                order_by('subject_prefix_tags')
            if not projects:
                break

            # fast path for the common case
            if len(projects) == 1:
                project = projects[0]
                break

            (_, prefixes) = clean_subject(mail.get('Subject'))
            catchall_project = None
            if not projects[0].get_subject_prefix_tags():
                catchall_project = projects[0]

            for p in projects:
                if not p.get_subject_prefix_tags():
                    continue

                for prefix in prefixes:
                    if prefix in p.get_subject_prefix_tags():
                        project = p

            if not project:
                project = catchall_project

    return project


def find_author(mail):

    from_header = clean_header(mail.get('From'))
    (name, email) = (None, None)

    # tuple of (regex, fn)
    #  - where fn returns a (name, email) tuple from the match groups resulting
    #    from re.match().groups()
    from_res = [
        # for "Firstname Lastname" <example@example.com> style addresses
        (re.compile(r'"?(.*?)"?\s*<([^>]+)>'), (lambda g: (g[0], g[1]))),

        # for example@example.com (Firstname Lastname) style addresses
        (re.compile(r'"?(.*?)"?\s*\(([^\)]+)\)'), (lambda g: (g[1], g[0]))),

        # everything else
        (re.compile(r'(.*)'), (lambda g: (None, g[0]))),
    ]

    for regex, fn in from_res:
        match = regex.match(from_header)
        if match:
            (name, email) = fn(match.groups())
            break

    if email is None:
        raise Exception("Could not parse From: header")

    email = email.strip()
    if name is not None:
        name = name.strip()

    new_person = False

    try:
        person = Person.objects.get(email__iexact=email)
    except Person.DoesNotExist:
        person = Person(name=name, email=email)
        new_person = True

    return (person, new_person)


def mail_date(mail):
    t = parsedate_tz(mail.get('Date', ''))
    if not t:
        return datetime.datetime.utcnow()
    return datetime.datetime.utcfromtimestamp(mktime_tz(t))


def mail_headers(mail):
    return reduce(operator.__concat__,
                  ['%s: %s\n' % (k, Header(v, header_name=k,
                                           continuation_ws='\t').encode())
                   for (k, v) in list(mail.items())])


def find_pull_request(content):
    git_re = re.compile(r'^The following changes since commit.*' +
                        r'^are available in the git repository at:\n'
                        r'^\s*([\S]+://[^\n]+)$',
                        re.DOTALL | re.MULTILINE)
    match = git_re.search(content)
    if match:
        return match.group(1)
    return None


def try_decode(payload, charset):
    try:
        payload = six.text_type(payload, charset)
    except UnicodeDecodeError:
        return None
    return payload


class MailContent:

    def __init__(self):
        self.patch = None
        self.comment = None
        self.series = None
        self.revision = None
        self.patch_order = 1    # place of the patch in the series
        self.filenames = []     # files touched by a diff


def build_references_from_headers(in_reply_to, references):
    refs = []

    if in_reply_to:
        refs.append(in_reply_to)

    if references:
        rs = references.split()
        rs.reverse()
        for r in rs:
            if r not in refs:
                refs.append(r)

    return refs


def get_object_by_msgid(cls, msgid):
    try:
        return cls.objects.get(msgid=msgid)
    except cls.DoesNotExist:
        return None
    except MultipleObjectsReturned:
        # it's theoritically possible to have the same message id for 2
        # patches or comments, take the more recent object then, why
        # not.
        return cls.objects.filter(msgid=msgid).order_by('-date')[0]


def find_header_in_text(headers, name):
    parser = HeaderParser()
    headers = parser.parsestr(headers)
    return headers[name]


def build_references_from_db(msgid):
    # msgid belongs to either a patch or a comment
    object = get_object_by_msgid(Patch, msgid)
    if not object:
        object = get_object_by_msgid(Comment, msgid)

    if not object:
        # cover letters are thread roots, but don't have a corresponding
        # Comment object as the cover letter is stored in Series.
        return []

    in_reply_to = find_header_in_text(object.headers, 'In-Reply-To')
    references = find_header_in_text(object.headers, 'References')
    refs = build_references_from_headers(in_reply_to, references)

    if not refs:
        return []

    # note that we recurse on the highest ancestor found, not necessarily the
    # immediate parent (depends: if the mail found in the DB is from a
    # actually MUA which filled in the 'References:' header or if it is a
    # git send-email mail, with only 'In-References-To: defined
    ancestor_msgid = refs[-1]
    return refs + build_references_from_db(ancestor_msgid)


def build_references_from_mail(mail):
    return build_references_from_headers(mail.get('In-Reply-To', None),
                                         mail.get('References', None))


def build_references_list(mail):
    """Construct the list of msgids from 'mail' to the root of the thread"""

    # parse the information from the mail headers
    refs = build_references_from_mail(mail)

    if not refs:
        return refs

    # Emails aren't required to have the full list of their parents in
    # References:. So we need to use the db to reach the root message.
    #
    # git send-email emails with --in-reply-to are the ultimate occurrence of
    # this behaviour as they just have the but just the direct parent in
    # References.
    parent_msgid = refs[-1]
    return refs + build_references_from_db(parent_msgid)


def parse_series_marker(subject_prefixes):
    """If this patch is part a of multi-patches series, ie has x/n in its
       subject, return (x, n). Otherwise, return (None, None)."""

    regex = re.compile('^([0-9]+)/([0-9]+)$')
    for prefix in subject_prefixes:
        m = regex.match(prefix)
        if not m:
            continue
        return (int(m.group(1)), int(m.group(2)))
    return (None, None)


def is_git_send_email(mail):
    return mail.get('X-Mailer', '').startswith('git-send-email ') or \
        'git-send-email' in mail.get('Message-ID', '')


def find_content(project, mail):
    patchbuf = None
    commentbuf = ''
    pullurl = None
    is_attachment = False

    for part in mail.walk():
        if part.get_content_maintype() != 'text':
            continue

        payload = part.get_payload(decode=True)
        subtype = part.get_content_subtype()

        if not isinstance(payload, six.text_type):
            charset = part.get_content_charset()

            # Check that we have a charset that we understand. Otherwise,
            # ignore it and fallback to our standard set.
            if charset is not None:
                try:
                    codecs.lookup(charset)
                except LookupError:
                    charset = None

            # If there is no charset or if it is unknown, then try some common
            # charsets before we fail.
            if charset is None:
                try_charsets = ['utf-8', 'windows-1252', 'iso-8859-1']
            else:
                try_charsets = [charset]

            for cset in try_charsets:
                decoded_payload = try_decode(payload, cset)
                if decoded_payload is not None:
                    break
            payload = decoded_payload

            # Could not find a valid decoded payload.  Fail.
            if payload is None:
                return None

        if subtype in ['x-patch', 'x-diff']:
            is_attachment = True
            patchbuf = payload

        elif subtype == 'plain':
            c = payload

            if not patchbuf:
                (patchbuf, c) = parse_patch(payload)

            if not pullurl:
                pullurl = find_pull_request(payload)

            if c is not None:
                commentbuf += c.strip() + '\n'

    ret = MailContent()

    drop_prefixes = [project.linkname] + project.get_subject_prefix_tags()
    (name, prefixes) = clean_subject(mail.get('Subject'), drop_prefixes)
    (x, n) = parse_series_marker(prefixes)
    refs = build_references_list(mail)
    is_root = refs == []
    is_cover_letter = is_root and x == 0
    is_patch = patchbuf is not None

    drop_patch = not is_attachment and \
        project.git_send_email_only and not is_git_send_email(mail)

    if pullurl or (is_patch and not drop_patch):
        if project.git_send_email_only or not is_cover_letter:
            ret.patch_order = x or 1
            ret.patch = Patch(name=name, pull_url=pullurl, content=patchbuf,
                              date=mail_date(mail), headers=mail_headers(mail))

    if patchbuf:
        ret.filenames = patch_get_filenames(patchbuf)

    # Create/update the Series and SeriesRevision objects
    if is_cover_letter or is_patch:
        msgid = mail.get('Message-Id').strip()

        # Series get a generic name when they don't start by a cover letter or
        # when they haven't received the root message yet. Except when it's
        # only 1 patch, then the series takes the patch subject as name.
        series_name = None
        if is_cover_letter or n is None:
            series_name = strip_prefixes(name)

        (ret.series, ret.revision, ret.patch_order, n) = \
            find_series_for_mail(project, series_name, msgid, is_patch,
                                 ret.patch_order, n, refs)
        ret.revision.n_patches = n or 1

        date = mail_date(mail)
        if not ret.series.submitted or date < ret.series.submitted:
            ret.series.submitted = date

    if is_cover_letter:
        ret.revision.cover_letter = clean_content(commentbuf)
        return ret

    if commentbuf:
        # If this is a new patch, we defer setting comment.patch until
        # patch has been saved by the caller
        if ret.patch:
            ret.comment = Comment(date=mail_date(mail),
                                  content=clean_content(commentbuf),
                                  headers=mail_headers(mail))

        else:
            cpatch = find_patch_for_comment(project, refs)
            if not cpatch:
                return ret
            ret.comment = Comment(patch=cpatch, date=mail_date(mail),
                                  content=clean_content(commentbuf),
                                  headers=mail_headers(mail))

    # make sure we always have a valid (series,revision) tuple if we have a
    # patch. We don't consider pull requests a series.
    if ret.patch and not pullurl and (not ret.series or not ret.revision):
        raise Exception("Could not find series for: %s" % name)

    return ret


def find_previous_patch(project, revision, order, refs):
    if not refs:
        return None

    # if one of the parents was a patch, this is an update. Well, almost. We
    # also need to make sure we don't match a patch from a series without a
    # cover letter (see comment below).
    parent_patch = None
    for ref in refs:
        try:
            patch = Patch.objects.get(project=project, msgid=ref)
            parent_patch = patch
            break
        except Patch.DoesNotExist:
            continue

    if not parent_patch:
        return None

    # A multiple patch series, sent without a cover letter (we don't cover the
    # case where patch i + 1 is sent as reply to patch i) will look like:
    # - root message (patch 1/n)
    #   - reply 1 (patch 2/n)
    #   - reply 2 (patch 3/n)
    #   - ...
    #   - reply n-1 (patch n/n)
    # We don't want to consider reply 1 to n-1 as new revisions of patch 1/n.
    #
    # However, we still want to be able to send a "PATCH v2 1/n" as a reply to
    # the root message.
    if revision.root_msgid != parent_patch.msgid or order == 1:
        return parent_patch

    return None


def find_patch_order(revisions, previous_patch, order, n_patches):
    # cycle through revisions starting by the more recent one and find
    # the revision where previous_patch is
    for revision in revisions:
        try:
            order = SeriesRevisionPatch.objects.get(revision=revision,
                                                    patch=previous_patch).order
            if n_patches is None:
                n_patches = revision.n_patches
            break
        except SeriesRevisionPatch.DoesNotExist:
            continue
    assert order is not None
    return (order, n_patches)


# The complexity here is because:
#   - patches can be received out of order: If we receive a patch, part of
#     series, before the root message, we create a placeholder series that will
#     be updated once we receive the root message.
#   - we need to create new revisions when the mail is actually a new version
#     of a previous patch
def find_series_for_mail(project, name, msgid, is_patch, order, n_patches,
                         refs):
    if refs == []:
        root_msgid = msgid
    else:
        root_msgid = refs[-1]

    try:
        # grab the latest revision for this mail thread
        revisions = SeriesRevision.objects.filter(series__project=project,
                                                  root_msgid=root_msgid) \
            .reverse()
        revision = revisions[0]
        series = revision.series
        if name:
            series.name = name
        if is_patch:
            previous_patch = find_previous_patch(project, revision,
                                                 order, refs)
            if previous_patch:
                (order, n_patches) = find_patch_order(revisions,
                                                      previous_patch,
                                                      order, n_patches)
                revision = revision.duplicate(exclude_patches=(order,))
                # series has been updated, grab the new instance
                series = revision.series
    except IndexError:
        if not name:
            name = SERIES_DEFAULT_NAME
        series = Series(name=name)
        revision = SeriesRevision(root_msgid=root_msgid)

    return (series, revision, order, n_patches)


def find_patch_for_comment(project, refs):
    for ref in refs:
        patch = None

        # first, check for a direct reply
        try:
            patch = Patch.objects.get(project=project, msgid=ref)
            return patch
        except Patch.DoesNotExist:
            pass

        # see if we have comments that refer to a patch
        try:
            comment = Comment.objects.get(patch__project=project, msgid=ref)
            return comment.patch
        except Comment.DoesNotExist:
            pass

    return None


split_re = re.compile(r'[,\s]+')


def split_prefixes(prefix):
    """ Turn a prefix string into a list of prefix tokens """

    matches = split_re.split(prefix)
    return [s for s in matches if s != '']


re_re = re.compile(r'^(re|fwd?)[:\s]\s*', re.I)
prefix_re = re.compile(r'^\[([^\]]*)\]\s*(.*)$')


def clean_subject(subject, drop_prefixes=None):
    """ Clean a Subject: header from an incoming patch.

    Removes Re: and Fwd: strings, as well as [PATCH]-style prefixes. By
    default, only [PATCH] is removed, and we keep any other bracketed data
    in the subject. If drop_prefixes is provided, remove those too,
    comparing case-insensitively."""

    subject = clean_header(subject)

    if drop_prefixes is None:
        drop_prefixes = []
    else:
        drop_prefixes = [s.lower() for s in drop_prefixes]

    drop_prefixes.append('patch')

    # remove Re:, Fwd:, etc
    subject = re_re.sub(' ', subject)

    subject = normalise_space(subject)

    prefixes = []

    match = prefix_re.match(subject)

    while match:
        prefix_str = match.group(1)
        prefixes += [p for p in split_prefixes(prefix_str)
                     if p.lower() not in drop_prefixes]

        subject = match.group(2)
        match = prefix_re.match(subject)

    subject = normalise_space(subject)

    subject = subject.strip()
    if prefixes:
        subject = '[%s] %s' % (','.join(prefixes), subject)

    return (subject, prefixes)


prefixes_re = re.compile(r'^\[[^\]]*\]\s*')


def strip_prefixes(subject):
    return prefixes_re.sub('', subject)


sig_re = re.compile(r'^(-- |_+)\n.*', re.S | re.M)


def clean_content(str):
    """ Try to remove signature (-- ) and list footer (_____) cruft """
    str = sig_re.sub('', str)
    return str.strip()


def get_state(state_name):
    """ Return the state with the given name or the default State """
    if state_name:
        try:
            return State.objects.get(name__iexact=state_name)
        except State.DoesNotExist:
            pass
    return get_default_initial_patch_state()


def auto_delegate(project, filenames):
    if not filenames:
        return None

    rules = list(DelegationRule.objects.filter(project=project))

    patch_delegate = None

    for filename in filenames:
        file_delegate = None
        for rule in rules:
            if fnmatch(filename, rule.path):
                file_delegate = rule.user
                break

        if file_delegate is None:
            return None

        if patch_delegate is not None and file_delegate != patch_delegate:
            return None

        patch_delegate = file_delegate

    return patch_delegate


def get_delegate(delegate_email):
    """ Return the delegate with the given email or None """
    if delegate_email:
        try:
            return User.objects.get(email__iexact=delegate_email)
        except User.DoesNotExist:
            pass
    return None


series_name_re = re.compile(r'[, \(]*(v|take)[\) 0-9]+$', re.I)


def clean_series_name(str):
    """Try to remove 'v2' and 'take 28' markers in cover letters subjects"""
    str = series_name_re.sub('', str)
    return str.strip()


def on_revision_complete(sender, revision, **kwargs):
    # Brand new series (revision.version == 1) may be updates to a Series
    # previously posted. Hook the SeriesRevision to the previous series then.
    if revision.version != 1:
        return

    new_series = revision.series
    if new_series.name == SERIES_DEFAULT_NAME:
        return

    name = clean_series_name(new_series.name)
    previous_series = Series.objects.filter(
            Q(project=new_series.project),
            Q(name__iexact=name) & ~Q(pk=new_series.pk))
    if len(previous_series) != 1:
        return

    previous_series = previous_series[0]
    new_revision = previous_series.latest_revision().duplicate_meta()
    new_revision.root_msgid = revision.root_msgid
    new_revision.cover_letter = revision.cover_letter
    new_revision.n_patches = revision.n_patches
    new_revision.save()
    i = 1
    for patch in revision.ordered_patches():
        new_revision.add_patch(patch, i)
        i += 1

    revision.delete()
    new_series.delete()


def parse_mail(mail):

    # some basic sanity checks
    if 'From' not in mail:
        LOGGER.debug("Ignoring mail due to missing 'From'")
        return 1

    if 'Subject' not in mail:
        LOGGER.debug("Ignoring mail due to missing 'Subject'")
        return 1

    if 'Message-Id' not in mail:
        LOGGER.debug("Ignoring mail due to missing 'Message-Id'")
        return 1

    hint = mail.get('X-Patchwork-Hint', '').lower()
    if hint == 'ignore':
        LOGGER.debug("Ignoring mail due to 'ignore' hint")
        return 0

    project = find_project(mail)
    if project is None:
        LOGGER.error('Failed to find a project for mail')
        return 1

    msgid = mail.get('Message-Id').strip()

    (author, save_required) = find_author(mail)

    content = find_content(project, mail)
    if not content:
        return 0
    patch = content.patch
    comment = content.comment
    series = content.series
    revision = content.revision

    series_revision_complete.connect(on_revision_complete)

    if series:
        if save_required:
            author.save()
            save_required = False
        series.project = project
        series.submitter = author
        series.save()
        LOGGER.debug('Series saved')

    if revision:
        revision.series = series
        revision.save()
        LOGGER.debug('Revision saved')

    if patch:
        delegate = get_delegate(mail.get('X-Patchwork-Delegate', '').strip())
        if not delegate:
            delegate = auto_delegate(project, content.filenames)

        # we delay the saving until we know we have a patch.
        if save_required:
            author.save()
            save_required = False
        patch.submitter = author
        patch.msgid = msgid
        patch.project = project
        patch.state = get_state(mail.get('X-Patchwork-State', '').strip())
        patch.delegate = delegate
        patch.save()
        if revision:
            revision.add_patch(patch, content.patch_order)
        LOGGER.debug('Patch saved')

    if comment:
        if save_required:
            author.save()
        # we defer this assignment until we know that we have a saved patch
        if patch:
            comment.patch = patch
        comment.submitter = author
        comment.msgid = msgid
        comment.save()
        LOGGER.debug('Comment saved')

    series_revision_complete.disconnect(on_revision_complete)

    return 0


extra_error_message = '''
== Mail

%(mail)s


== Traceback

'''


# Send emails to settings.ADMINS when encountering errors
def setup_error_handler():
    if settings.DEBUG:
        return None

    mail_handler = AdminEmailHandler()
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(logging.Formatter(extra_error_message))

    logger = logging.getLogger('patchwork')
    logger.addHandler(mail_handler)

    return logger


_lockref = None


def lock():
    global _lockref

    l = _lockref and _lockref()
    if l is not None and l.held:
        l.lock()
        return l

    l = lockmod.lock("/tmp/patchwork.parsemail.lock", timeout=60)
    _lockref = weakref.ref(l)
    return l


def main(args):
    django.setup()
    logger = setup_error_handler()
    parser = argparse.ArgumentParser()
    parse_lock = None

    def list_logging_levels():
        """Give a summary of all available logging levels."""
        return sorted(list(VERBOSITY_LEVELS.keys()),
                      key=lambda x: VERBOSITY_LEVELS[x])

    parser.add_argument('--verbosity', choices=list_logging_levels(),
                        help='logging level', default='info')

    args = vars(parser.parse_args())

    logging.basicConfig(level=VERBOSITY_LEVELS[args['verbosity']])

    mail = message_from_file(sys.stdin)
    try:
        parse_lock = lock()
        return parse_mail(mail)
    except:
        if logger:
            logger.exception('Error when parsing incoming email', extra={
                'mail': mail.as_string(),
            })
        raise
    finally:
        release(parse_lock)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
