# Patchwork - automated patch tracking system
# Copyright (C) 2008 Jeremy Kerr <jk@ozlabs.org>
# Copyright (C) 2015 Intel Corporation
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

from django.contrib import auth
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.conf import settings
from django.db import models
from django.db.models import Q
import django.dispatch
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.six import add_metaclass
import jsonfield

from patchwork.parser import hash_patch, extract_tags

import re
import datetime
import time
import random
from collections import Counter, OrderedDict


@python_2_unicode_compatible
class Person(models.Model):
    email = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, null=True, blank=True,
                             on_delete=models.SET_NULL)

    def display_name(self):
        if self.name:
            return self.name
        else:
            return self.email

    def email_name(self):
        if (self.name):
            return "%s <%s>" % (self.name, self.email)
        else:
            return self.email

    def link_to_user(self, user):
        self.name = user.profile.name()
        self.user = user

    def __str__(self):
        return self.display_name()

    class Meta:
        verbose_name_plural = 'People'


def get_comma_separated_field(value):
    if not value:
        return []
    tags = [v.strip() for v in value.split(',')]
    tags = [tag for tag in tags if tag]
    return tags


@python_2_unicode_compatible
class Project(models.Model):
    linkname = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    listid = models.CharField(max_length=255)
    listemail = models.CharField(max_length=200)
    web_url = models.CharField(max_length=2000, blank=True)
    scm_url = models.CharField(max_length=2000, blank=True)
    webscm_url = models.CharField(max_length=2000, blank=True)
    send_notifications = models.BooleanField(default=False)
    use_tags = models.BooleanField(default=True)
    git_send_email_only = models.BooleanField(default=False)
    subject_prefix_tags = models.CharField(max_length=255, blank=True,
                                           help_text='Comma separated list of tags')

    def is_editable(self, user):
        if not user.is_authenticated():
            return False
        return self in user.profile.maintainer_projects.all()

    @cached_property
    def tags(self):
        if not self.use_tags:
            return []
        return list(Tag.objects.all())

    def get_subject_prefix_tags(self):
        return get_comma_separated_field(self.subject_prefix_tags)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['linkname']


def user_name(user):
    if user.first_name or user.last_name:
        names = list(filter(bool, [user.first_name, user.last_name]))
        return u' '.join(names)
    return user.username

auth.models.User.add_to_class('name', user_name)


@python_2_unicode_compatible
class DelegationRule(models.Model):
    user = models.ForeignKey(User)
    path = models.CharField(max_length=255)
    project = models.ForeignKey(Project)
    priority = models.IntegerField(default=0)

    def __str__(self):
        return self.path

    class Meta:
        ordering = ['-priority', 'path']
        unique_together = (('path', 'project'))


@python_2_unicode_compatible
class UserProfile(models.Model):
    user = models.OneToOneField(User, unique=True, related_name='profile')
    primary_project = models.ForeignKey(Project, null=True, blank=True)
    maintainer_projects = models.ManyToManyField(Project,
                                                 related_name='maintainer_project')
    send_email = models.BooleanField(default=False,
                                     help_text='Selecting this option allows patchwork to send ' +
                                     'email on your behalf')
    patches_per_page = models.PositiveIntegerField(default=100,
                                                   null=False, blank=False,
                                                   help_text='Number of patches to display per page')

    def name(self):
        return user_name(self.user)

    def contributor_projects(self):
        submitters = Person.objects.filter(user=self.user)
        return Project.objects.filter(id__in=Patch.objects.filter(
            submitter__in=submitters)
            .values('project_id').query)

    def sync_person(self):
        pass

    def n_todo_patches(self):
        return self.todo_patches().count()

    def todo_patches(self, project=None):

        # filter on project, if necessary
        if project:
            qs = Patch.objects.filter(project=project)
        else:
            qs = Patch.objects

        qs = qs.filter(archived=False) \
            .filter(delegate=self.user) \
            .filter(state__in=State.objects.filter(action_required=True)
                    .values('pk').query)
        return qs

    def __str__(self):
        return self.name()


def _user_saved_callback(sender, created, instance, **kwargs):
    try:
        profile = instance.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=instance)
    profile.save()

models.signals.post_save.connect(_user_saved_callback, sender=User)


@python_2_unicode_compatible
class State(models.Model):
    name = models.CharField(max_length=100)
    ordering = models.IntegerField(unique=True)
    action_required = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['ordering']


@add_metaclass(models.SubfieldBase)
class HashField(models.CharField):

    def __init__(self, algorithm='sha1', *args, **kwargs):
        self.algorithm = algorithm
        try:
            import hashlib

            def _construct(string=''):
                if isinstance(string, six.text_type):
                    string = string.encode('utf-8')
                return hashlib.new(self.algorithm, string)
            self.construct = _construct
            self.n_bytes = len(hashlib.new(self.algorithm).hexdigest())
        except ImportError:
            modules = {'sha1': 'sha', 'md5': 'md5'}

            if algorithm not in modules:
                raise NameError("Unknown algorithm '%s'" % algorithm)

            self.construct = __import__(modules[algorithm]).new

        self.n_bytes = len(self.construct().hexdigest())

        kwargs['max_length'] = self.n_bytes
        super(HashField, self).__init__(*args, **kwargs)

    def db_type(self, connection=None):
        return 'char(%d)' % self.n_bytes


@python_2_unicode_compatible
class Tag(models.Model):
    name = models.CharField(max_length=20)
    pattern = models.CharField(max_length=50,
                               help_text='A simple regex to match the tag in the content of '
                               'a message. Will be used with MULTILINE and IGNORECASE '
                               'flags. eg. ^Acked-by:')
    abbrev = models.CharField(max_length=2, unique=True,
                              help_text='Short (one-or-two letter) abbreviation for the tag, '
                              'used in table column headers')

    @property
    def attr_name(self):
        return 'tag_%d_count' % self.id

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['abbrev']


class PatchTag(models.Model):
    patch = models.ForeignKey('Patch')
    tag = models.ForeignKey('Tag')
    count = models.IntegerField(default=1)

    class Meta:
        unique_together = [('patch', 'tag')]


def get_default_initial_patch_state():
    return State.objects.get(ordering=0)


class PatchQuerySet(models.query.QuerySet):

    def with_tag_counts(self, project):
        if not project.use_tags:
            return self

        # We need the project's use_tags field loaded for Project.tags().
        # Using prefetch_related means we'll share the one instance of
        # Project, and share the project.tags cache between all patch.project
        # references.
        qs = self.prefetch_related('project')
        select = OrderedDict()
        select_params = []
        for tag in project.tags:
            select[tag.attr_name] = ("coalesce("
                                     "(SELECT count FROM patchwork_patchtag "
                                     "WHERE patchwork_patchtag.patch_id=patchwork_patch.id "
                                     "AND patchwork_patchtag.tag_id=%s), 0)")
            select_params.append(tag.id)

        return qs.extra(select=select, select_params=select_params)


class PatchManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return PatchQuerySet(self.model, using=self.db)

    def with_tag_counts(self, project):
        return self.get_queryset().with_tag_counts(project)


def filename(name, ext):
    fname_re = re.compile('[^-_A-Za-z0-9\.]+')
    str = fname_re.sub('-', name)
    return str.strip('-') + ext


@python_2_unicode_compatible
class Patch(models.Model):
    project = models.ForeignKey(Project)
    msgid = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    date = models.DateTimeField(default=datetime.datetime.now)
    submitter = models.ForeignKey(Person)
    delegate = models.ForeignKey(User, blank=True, null=True)
    state = models.ForeignKey(State, null=True)
    archived = models.BooleanField(default=False)
    headers = models.TextField(blank=True)
    content = models.TextField(null=True, blank=True)
    pull_url = models.CharField(max_length=255, null=True, blank=True)
    commit_ref = models.CharField(max_length=255, null=True, blank=True)
    hash = HashField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, through=PatchTag)

    objects = PatchManager()

    def commit_message(self):
        """Retrieves the commit message"""
        return Comment.objects.filter(patch=self, msgid=self.msgid)

    def answers(self):
        """Retrieves the answers (ie all comments but the commit message)"""
        return Comment.objects.filter(Q(patch=self) & ~Q(msgid=self.msgid))

    def comments(self):
        """Retrieves all comments of this patch ie. the commit message and the
           answers"""
        return Comment.objects.filter(patch=self)

    def _set_tag(self, tag, count):
        if count == 0:
            self.patchtag_set.filter(tag=tag).delete()
            return
        (patchtag, _) = PatchTag.objects.get_or_create(patch=self, tag=tag)
        if patchtag.count != count:
            patchtag.count = count
            patchtag.save()

    def refresh_tag_counts(self):
        tags = self.project.tags
        counter = Counter()
        for comment in self.comment_set.all():
            counter = counter + extract_tags(comment.content, tags)

        for tag in tags:
            self._set_tag(tag, counter[tag])

    def save(self):
        if not hasattr(self, 'state') or not self.state:
            self.state = get_default_initial_patch_state()

        if self.hash is None and self.content is not None:
            self.hash = hash_patch(self.content).hexdigest()

        super(Patch, self).save()

    def is_editable(self, user):
        if not user.is_authenticated():
            return False

        if self.submitter.user == user or self.delegate == user:
            return True

        return self.project.is_editable(user)

    def filename(self):
        return filename(self.name, '.patch')

    @models.permalink
    def get_absolute_url(self):
        return ('patchwork.views.patch.patch', (), {'patch_id': self.id})

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Patches'
        ordering = ['date']
        unique_together = [('msgid', 'project')]


class Comment(models.Model):
    patch = models.ForeignKey(Patch)
    msgid = models.CharField(max_length=255)
    submitter = models.ForeignKey(Person)
    date = models.DateTimeField(default=datetime.datetime.now)
    headers = models.TextField(blank=True)
    content = models.TextField()

    response_re = re.compile(
        '^(Tested|Reviewed|Acked|Signed-off|Nacked|Reported)-by: .*$',
        re.M | re.I)

    def patch_responses(self):
        return ''.join([match.group(0) + '\n' for match in
                        self.response_re.finditer(self.content)])

    def save(self, *args, **kwargs):
        super(Comment, self).save(*args, **kwargs)
        self.patch.refresh_tag_counts()

    def delete(self, *args, **kwargs):
        super(Comment, self).delete(*args, **kwargs)
        self.patch.refresh_tag_counts()

    class Meta:
        ordering = ['date']
        unique_together = [('msgid', 'patch')]


class Bundle(models.Model):
    owner = models.ForeignKey(User)
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=50, null=False, blank=False)
    patches = models.ManyToManyField(Patch, through='BundlePatch')
    public = models.BooleanField(default=False)

    def n_patches(self):
        return self.patches.all().count()

    def ordered_patches(self):
        return self.patches.order_by('bundlepatch__order')

    def append_patch(self, patch):
        # todo: use the aggregate queries in django 1.1
        orders = BundlePatch.objects.filter(bundle=self).order_by('-order') \
            .values('order')

        if len(orders) > 0:
            max_order = orders[0]['order']
        else:
            max_order = 0

        # see if the patch is already in this bundle
        if BundlePatch.objects.filter(bundle=self, patch=patch).count():
            raise Exception("patch is already in bundle")

        bp = BundlePatch.objects.create(bundle=self, patch=patch,
                                        order=max_order + 1)
        bp.save()

    def public_url(self):
        if not self.public:
            return None
        site = Site.objects.get_current()
        return 'http://%s%s' % (site.domain,
                                reverse('patchwork.views.bundle.bundle',
                                        kwargs={
                                            'username': self.owner.username,
                                            'bundlename': self.name
                                        }))

    @models.permalink
    def get_absolute_url(self):
        return ('patchwork.views.bundle.bundle', (), {
            'username': self.owner.username,
            'bundlename': self.name,
        })

    class Meta:
        unique_together = [('owner', 'name')]


class BundlePatch(models.Model):
    patch = models.ForeignKey(Patch)
    bundle = models.ForeignKey(Bundle)
    order = models.IntegerField()

    class Meta:
        unique_together = [('bundle', 'patch')]
        ordering = ['order']

SERIES_DEFAULT_NAME = "Series without cover letter"


class TestState:
    STATE_PENDING = 0
    STATE_SUCCESS = 1
    STATE_WARNING = 2
    STATE_FAILURE = 3
    STATE_CHOICES = (
        (STATE_PENDING, 'pending'),
        (STATE_SUCCESS, 'success'),
        (STATE_WARNING, 'warning'),
        (STATE_FAILURE, 'failure'),
    )

    @classmethod
    def from_string(cls, s):
        s2i = {s: i for i, s in cls.STATE_CHOICES}
        return s2i[s]


# This Model represents the "top level" Series, an object that doesn't change
# with the various versions of patches sent to the mailing list.
@python_2_unicode_compatible
class Series(models.Model):
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=200, default=SERIES_DEFAULT_NAME)
    submitter = models.ForeignKey(Person, related_name='submitters')
    reviewer = models.ForeignKey(User, related_name='reviewers', null=True,
                                 blank=True)
    submitted = models.DateTimeField(default=datetime.datetime.now)
    last_updated = models.DateTimeField(auto_now=True)
    # direct access to the latest revision so we can get the latest revision
    # information with a JOIN
    last_revision = models.OneToOneField('SeriesRevision', null=True,
                                         related_name='+')

    def revisions(self):
        return SeriesRevision.objects.filter(series=self)

    def latest_revision(self):
        return self.revisions().reverse()[0]

    def get_absolute_url(self):
        return reverse('series', kwargs={'series': self.pk})

    def dump(self):
        print('')
        print('===')
        print('Series: %s' % self)
        print('    version: %d' % self.version)
        print('    n_patches: %d' % self.n_patches)
        for rev in self.revisions():
            print('    rev %d:' % rev.version)
            i = 1
            for patch in rev.ordered_patches():
                print('        patch %d:' % i)
                print('            subject: %s' % patch.name)
                print('            msgid  : %s' % patch.msgid)
                i += 1

    def filename(self):
        return filename(self.name, '.mbox')

    def __str__(self):
        return self.name

# Signal one can listen to to know when a revision is complete (ie. has all of
# its patches)
series_revision_complete = django.dispatch.Signal(providing_args=["revision"])

# A 'revision' of a series. Resending a new version of a patch or a full new
# iteration of a series will create a new revision.


@python_2_unicode_compatible
class SeriesRevision(models.Model):
    series = models.ForeignKey(Series)
    version = models.IntegerField(default=1)
    root_msgid = models.CharField(max_length=255)
    cover_letter = models.TextField(null=True, blank=True)
    n_patches = models.IntegerField(default=0)
    patches = models.ManyToManyField(Patch, through='SeriesRevisionPatch')
    test_state = models.SmallIntegerField(choices=TestState.STATE_CHOICES,
                                          null=True)

    class Meta:
        unique_together = [('series', 'version')]
        ordering = ['version']

    def ordered_patches(self):
        return self.patches.order_by('seriesrevisionpatch__order')

    def add_patch(self, patch, order):
        # see if the patch is already in this revision
        if SeriesRevisionPatch.objects.filter(revision=self,
                                              patch=patch).count():
            raise Exception("patch is already in revision")

        sp = SeriesRevisionPatch.objects.create(revision=self, patch=patch,
                                                order=order)
        sp.save()

        revision_complete = self.patches.count() == self.n_patches
        if revision_complete:
            series_revision_complete.send(sender=self.__class__, revision=self)

    def duplicate_meta(self):
        new = SeriesRevision.objects.get(pk=self.pk)
        new.pk = None
        new.cover_letter = None
        new.version = self.version + 1
        new.test_state = None
        new.save()

        return new

    def duplicate(self, exclude_patches=()):
        """Create a new revision based on 'self', incrementing the version
           and populating the new revision with all 'self' patches.
           exclude_patch (a list of 'order's) can be used to exclude
           patches from the operation"""
        new = self.duplicate_meta()
        order = 0
        for p in self.ordered_patches():
            order += 1
            if order in exclude_patches:
                continue
            new.add_patch(p, order)
        return new

    def refresh_test_state(self):
        results = TestResult.objects.filter(revision=self)
        if results.count() > 0:
            self.test_state = max([r.state for r in results])
            self.save()
            self.series.save()

    def __str__(self):
        return "Revision " + str(self.version)


class SeriesRevisionPatch(models.Model):
    patch = models.ForeignKey(Patch)
    revision = models.ForeignKey(SeriesRevision)
    order = models.IntegerField()

    class Meta:
        unique_together = [('revision', 'patch'), ('revision', 'order')]
        ordering = ['order']


class Event(models.Model):
    name = models.CharField(max_length=20)


class EventLog(models.Model):
    event = models.ForeignKey(Event)
    event_time = models.DateTimeField(auto_now=True)
    series = models.ForeignKey(Series)
    user = models.ForeignKey(User, null=True)
    parameters = jsonfield.JSONField(null=True)

    class Meta:
        ordering = ['-event_time']


@python_2_unicode_compatible
class Test(models.Model):
    # no mail, default so test systems/scripts can have a grace period to
    # settle down and give useful results
    RECIPIENT_NONE = 0
    # send mail only to submitter
    RECIPIENT_SUBMITTER = 1
    # send mail to submitter and mailing-list in Cc
    RECIPIENT_MAILING_LIST = 2
    # send mail to the addresses listed in the mail_to_list field only
    RECIPIENT_TO_LIST = 3
    RECIPIENT_CHOICES = (
        (RECIPIENT_NONE, 'none'),
        (RECIPIENT_SUBMITTER, 'submitter'),
        (RECIPIENT_MAILING_LIST, 'mailing list'),
        (RECIPIENT_TO_LIST, 'recipient list'),
    )

    # send result mail on any state (but pending)
    CONDITION_ALWAYS = 0
    # only send result on warning/failure
    CONDITION_ON_FAILURE = 1
    CONDITION_CHOICES = (
        (CONDITION_ALWAYS, 'always'),
        (CONDITION_ON_FAILURE, 'on failure'),
    )

    project = models.ForeignKey(Project)
    name = models.CharField(max_length=255)
    mail_recipient = models.SmallIntegerField(choices=RECIPIENT_CHOICES,
                                              default=RECIPIENT_NONE)
    # email addresses in these lists are always added to the To: and Cc:fields,
    # unless we don't want to send any email at all.
    mail_to_list = models.CharField(max_length=255, blank=True, null=True,
                                    help_text='Comma separated list of emails')
    mail_cc_list = models.CharField(max_length=255, blank=True, null=True,
                                    help_text='Comma separated list of emails')
    mail_condition = models.SmallIntegerField(choices=CONDITION_CHOICES,
                                              default=CONDITION_ALWAYS)

    class Meta:
        unique_together = [('project', 'name')]

    def get_to_list(self):
        return get_comma_separated_field(self.mail_to_list)

    def get_cc_list(self):
        return get_comma_separated_field(self.mail_cc_list)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class TestResult(models.Model):

    test = models.ForeignKey(Test)
    revision = models.ForeignKey(SeriesRevision, blank=True, null=True)
    patch = models.ForeignKey(Patch, blank=True, null=True)
    user = models.ForeignKey(User)
    date = models.DateTimeField(auto_now=True)
    state = models.SmallIntegerField(choices=TestState.STATE_CHOICES)
    url = models.URLField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.get_state_display()

    class Meta:
        unique_together = [('test', 'revision'), ('test', 'patch')]


class EmailConfirmation(models.Model):
    validity = datetime.timedelta(days=settings.CONFIRMATION_VALIDITY_DAYS)
    type = models.CharField(max_length=20, choices=[
        ('userperson', 'User-Person association'),
        ('registration', 'Registration'),
        ('optout', 'Email opt-out'),
    ])
    email = models.CharField(max_length=200)
    user = models.ForeignKey(User, null=True)
    key = HashField()
    date = models.DateTimeField(default=datetime.datetime.now)
    active = models.BooleanField(default=True)

    def deactivate(self):
        self.active = False
        self.save()

    def is_valid(self):
        return self.date + self.validity > datetime.datetime.now()

    def save(self):
        max = 1 << 32
        if self.key == '':
            str = '%s%s%d' % (self.user, self.email, random.randint(0, max))
            self.key = self._meta.get_field('key').construct(str).hexdigest()
        super(EmailConfirmation, self).save()


@python_2_unicode_compatible
class EmailOptout(models.Model):
    email = models.CharField(max_length=200, primary_key=True)

    @classmethod
    def is_optout(cls, email):
        email = email.lower().strip()
        return cls.objects.filter(email=email).count() > 0

    def __str__(self):
        return self.email


class PatchChangeNotification(models.Model):
    patch = models.OneToOneField(Patch, primary_key=True)
    last_modified = models.DateTimeField(default=datetime.datetime.now)
    orig_state = models.ForeignKey(State)


def _patch_change_callback(sender, instance, **kwargs):
    # we only want notification of modified patches
    if instance.pk is None:
        return

    if instance.project is None or not instance.project.send_notifications:
        return

    try:
        orig_patch = Patch.objects.get(pk=instance.pk)
    except Patch.DoesNotExist:
        return

    # If there's no interesting changes, abort without creating the
    # notification
    if orig_patch.state == instance.state:
        return

    notification = None
    try:
        notification = PatchChangeNotification.objects.get(patch=instance)
    except PatchChangeNotification.DoesNotExist:
        pass

    if notification is None:
        notification = PatchChangeNotification(patch=instance,
                                               orig_state=orig_patch.state)

    elif notification.orig_state == instance.state:
        # If we're back at the original state, there is no need to notify
        notification.delete()
        return

    notification.last_modified = datetime.datetime.now()
    notification.save()

models.signals.pre_save.connect(_patch_change_callback, sender=Patch)


def _on_revision_complete(sender, revision, **kwargs):
    series = revision.series

    # update series.last_revision
    series.last_revision = series.latest_revision()
    series.save()

    # log event
    new_revision = Event.objects.get(name='series-new-revision')
    log = EventLog(event=new_revision, series=series,
                   user=series.submitter.user,
                   parameters={'revision': revision.version})
    log.save()

series_revision_complete.connect(_on_revision_complete)
