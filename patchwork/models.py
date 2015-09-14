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

from django.db import models
from django.db.models import Q
import django.dispatch
from django.contrib import auth
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.conf import settings
from django.utils.functional import cached_property
from patchwork.parser import hash_patch, extract_tags

import re
import datetime, time
import random
from collections import Counter, OrderedDict

class Person(models.Model):
    email = models.CharField(max_length=255, unique = True)
    name = models.CharField(max_length=255, null = True, blank = True)
    user = models.ForeignKey(User, null = True, blank = True,
            on_delete = models.SET_NULL)

    def display_name(self):
        if self.name:
            return self.name
        else:
            return self.email

    def __unicode__(self):
        return self.display_name()

    def link_to_user(self, user):
        self.name = user.profile.name()
        self.user = user

    class Meta:
        verbose_name_plural = 'People'

class Project(models.Model):
    linkname = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, unique=True)
    listid = models.CharField(max_length=255, unique=True)
    listemail = models.CharField(max_length=200)
    web_url = models.CharField(max_length=2000, blank=True)
    scm_url = models.CharField(max_length=2000, blank=True)
    webscm_url = models.CharField(max_length=2000, blank=True)
    send_notifications = models.BooleanField(default=False)
    use_tags = models.BooleanField(default=True)
    git_send_email_only = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def is_editable(self, user):
        if not user.is_authenticated():
            return False
        return self in user.profile.maintainer_projects.all()

    @cached_property
    def tags(self):
        if not self.use_tags:
            return []
        return list(Tag.objects.all())

    class Meta:
        ordering = ['linkname']

def user_name(user):
    if user.first_name or user.last_name:
        names = filter(bool, [user.first_name, user.last_name])
        return u' '.join(names)
    return user.username

auth.models.User.add_to_class('name', user_name)

class UserProfile(models.Model):
    user = models.OneToOneField(User, unique = True, related_name='profile')
    primary_project = models.ForeignKey(Project, null = True, blank = True)
    maintainer_projects = models.ManyToManyField(Project,
            related_name = 'maintainer_project')
    send_email = models.BooleanField(default = False,
            help_text = 'Selecting this option allows patchwork to send ' +
                'email on your behalf')
    patches_per_page = models.PositiveIntegerField(default = 100,
            null = False, blank = False,
            help_text = 'Number of patches to display per page')

    def name(self):
        return user_name(self.user)

    def contributor_projects(self):
        submitters = Person.objects.filter(user = self.user)
        return Project.objects.filter(id__in =
                                        Patch.objects.filter(
                                            submitter__in = submitters)
                                        .values('project_id').query)

    def sync_person(self):
        pass

    def n_todo_patches(self):
        return self.todo_patches().count()

    def todo_patches(self, project = None):

        # filter on project, if necessary
        if project:
            qs = Patch.objects.filter(project = project)
        else:
            qs = Patch.objects

        qs = qs.filter(archived = False) \
             .filter(delegate = self.user) \
             .filter(state__in =
                     State.objects.filter(action_required = True)
                         .values('pk').query)
        return qs

    def __unicode__(self):
        return self.name()

def _user_saved_callback(sender, created, instance, **kwargs):
    try:
        profile = instance.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile(user = instance)
    profile.save()

models.signals.post_save.connect(_user_saved_callback, sender = User)

class State(models.Model):
    name = models.CharField(max_length = 100)
    ordering = models.IntegerField(unique = True)
    action_required = models.BooleanField(default = True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['ordering']

class HashField(models.CharField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, algorithm = 'sha1', *args, **kwargs):
        self.algorithm = algorithm
        try:
            import hashlib
            def _construct(string = ''):
                return hashlib.new(self.algorithm, string)
            self.construct = _construct
            self.n_bytes = len(hashlib.new(self.algorithm).hexdigest())
        except ImportError:
            modules = { 'sha1': 'sha', 'md5': 'md5'}

            if algorithm not in modules.keys():
                raise NameError("Unknown algorithm '%s'" % algorithm)

            self.construct = __import__(modules[algorithm]).new

        self.n_bytes = len(self.construct().hexdigest())

        kwargs['max_length'] = self.n_bytes
        super(HashField, self).__init__(*args, **kwargs)

    def db_type(self, connection=None):
        return 'char(%d)' % self.n_bytes

class Tag(models.Model):
    name = models.CharField(max_length=20)
    pattern = models.CharField(max_length=50,
                help_text='A simple regex to match the tag in the content of '
                    'a message. Will be used with MULTILINE and IGNORECASE '
                    'flags. eg. ^Acked-by:')
    abbrev = models.CharField(max_length=2, unique=True,
                help_text='Short (one-or-two letter) abbreviation for the tag, '
                    'used in table column headers')

    def __unicode__(self):
        return self.name

    @property
    def attr_name(self):
        return 'tag_%d_count' % self.id

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

class Patch(models.Model):
    project = models.ForeignKey(Project)
    msgid = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    date = models.DateTimeField(default=datetime.datetime.now)
    submitter = models.ForeignKey(Person)
    delegate = models.ForeignKey(User, blank = True, null = True)
    state = models.ForeignKey(State, null=True)
    archived = models.BooleanField(default = False)
    headers = models.TextField(blank = True)
    content = models.TextField(null = True, blank = True)
    pull_url = models.CharField(max_length=255, null = True, blank = True)
    commit_ref = models.CharField(max_length=255, null = True, blank = True)
    hash = HashField(null = True, blank = True)
    tags = models.ManyToManyField(Tag, through=PatchTag)

    objects = PatchManager()

    def __unicode__(self):
        return self.name

    def commit_message(self):
        """Retrieves the commit message"""
        return Comment.objects.filter(patch=self, msgid=self.msgid)

    def answers(self):
        """Retrieves the answers (ie all comments but the commit message)"""
        return Comment.objects.filter(Q(patch=self) & ~Q(msgid=self.msgid))

    def comments(self):
        """Retrieves all comments of this patch ie. the commit message and the
           answers"""
        return Comment.objects.filter(patch = self)

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
        fname_re = re.compile('[^-_A-Za-z0-9\.]+')
        str = fname_re.sub('-', self.name)
        return str.strip('-') + '.patch'

    @models.permalink
    def get_absolute_url(self):
        return ('patchwork.views.patch.patch', (), {'patch_id': self.id})

    class Meta:
        verbose_name_plural = 'Patches'
        ordering = ['date']
        unique_together = [('msgid', 'project')]

class Comment(models.Model):
    patch = models.ForeignKey(Patch)
    msgid = models.CharField(max_length=255)
    submitter = models.ForeignKey(Person)
    date = models.DateTimeField(default = datetime.datetime.now)
    headers = models.TextField(blank = True)
    content = models.TextField()

    response_re = re.compile( \
            '^(Tested|Reviewed|Acked|Signed-off|Nacked|Reported)-by: .*$',
            re.M | re.I)

    def patch_responses(self):
        return ''.join([ match.group(0) + '\n' for match in
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
    name = models.CharField(max_length = 50, null = False, blank = False)
    patches = models.ManyToManyField(Patch, through = 'BundlePatch')
    public = models.BooleanField(default = False)

    def n_patches(self):
        return self.patches.all().count()

    def ordered_patches(self):
        return self.patches.order_by('bundlepatch__order')

    def append_patch(self, patch):
        # todo: use the aggregate queries in django 1.1
        orders = BundlePatch.objects.filter(bundle = self).order_by('-order') \
                 .values('order')

        if len(orders) > 0:
            max_order = orders[0]['order']
        else:
            max_order = 0

        # see if the patch is already in this bundle
        if BundlePatch.objects.filter(bundle = self, patch = patch).count():
            raise Exception("patch is already in bundle")

        bp = BundlePatch.objects.create(bundle = self, patch = patch,
                order = max_order + 1)
        bp.save()

    class Meta:
        unique_together = [('owner', 'name')]

    def public_url(self):
        if not self.public:
            return None
        site = Site.objects.get_current()
        return 'http://%s%s' % (site.domain,
                reverse('patchwork.views.bundle.bundle',
                        kwargs = {
                                'username': self.owner.username,
                                'bundlename': self.name
                        }))

    @models.permalink
    def get_absolute_url(self):
        return ('patchwork.views.bundle.bundle', (), {
                                'username': self.owner.username,
                                'bundlename': self.name,
                            })

class BundlePatch(models.Model):
    patch = models.ForeignKey(Patch)
    bundle = models.ForeignKey(Bundle)
    order = models.IntegerField()

    class Meta:
        unique_together = [('bundle', 'patch')]
        ordering = ['order']

SERIES_DEFAULT_NAME = "Series without cover letter"

# This Model represents the "top level" Series, an object that doesn't change
# with the various versions of patches sent to the mailing list.
class Series(models.Model):
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=200, default=SERIES_DEFAULT_NAME)
    submitter = models.ForeignKey(Person, related_name='submitters')
    reviewer = models.ForeignKey(User, related_name='reviewers', null=True,
                                 blank=True)
    submitted = models.DateTimeField(default=datetime.datetime.now)
    last_updated = models.DateTimeField(auto_now=True)
    # Caches the latest version so we can display it without looking at the max
    # of all SeriesRevision.version
    version = models.IntegerField(default=1)
    # This is the number of patches of the latest version.
    n_patches = models.IntegerField(default=0)

    def __unicode__(self):
        return self.name

    def revisions(self):
        return SeriesRevision.objects.filter(series=self)

    def latest_revision(self):
        return self.revisions().reverse()[0]

    def get_absolute_url(self):
        return reverse('series', kwargs={ 'series': self.pk })

    def dump(self):
        print('')
        print('===')
        print('Series: %s' % self)
        print('    version %d' % self.version)
        for rev in self.revisions():
            print('    rev %d:' % rev.version)
            i = 1
            for patch in rev.ordered_patches():
                print('        patch %d:' % i)
                print('            subject: %s' % patch.name)
                print('            msgid  : %s' % patch.msgid)
                i += 1

# Signal one can listen to to know when a revision is complete (ie. has all of
# its patches)
series_revision_complete = django.dispatch.Signal(providing_args=["revision"])

# A 'revision' of a series. Resending a new version of a patch or a full new
# iteration of a series will create a new revision.
class SeriesRevision(models.Model):
    series = models.ForeignKey(Series)
    version = models.IntegerField(default=1)
    root_msgid = models.CharField(max_length=255)
    cover_letter = models.TextField(null = True, blank = True)
    patches = models.ManyToManyField(Patch, through = 'SeriesRevisionPatch')

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

        revision_complete = self.patches.count() == self.series.n_patches
        if revision_complete:
            series_revision_complete.send(sender=self.__class__, revision=self)

    def duplicate_meta(self):
        new = SeriesRevision.objects.get(pk=self.pk)
        new.pk = None
        new.cover_letter = None
        new.version = self.version + 1
        new.save()

        series = new.series
        series.version = new.version
        series.save()

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

    def __unicode__(self):
        if hasattr(self, 'series'):
            return self.series.name + " (rev " + str(self.version) + ")"
        else:
            return "New revision" + " (rev " + str(self.version) + ")"

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

    class Meta:
        ordering = ['-event_time']

class EmailConfirmation(models.Model):
    validity = datetime.timedelta(days = settings.CONFIRMATION_VALIDITY_DAYS)
    type = models.CharField(max_length = 20, choices = [
                                ('userperson', 'User-Person association'),
                                ('registration', 'Registration'),
                                ('optout', 'Email opt-out'),
                            ])
    email = models.CharField(max_length = 200)
    user = models.ForeignKey(User, null = True)
    key = HashField()
    date = models.DateTimeField(default = datetime.datetime.now)
    active = models.BooleanField(default = True)

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

class EmailOptout(models.Model):
    email = models.CharField(max_length = 200, primary_key = True)

    def __unicode__(self):
        return self.email

    @classmethod
    def is_optout(cls, email):
        email = email.lower().strip()
        return cls.objects.filter(email = email).count() > 0

class PatchChangeNotification(models.Model):
    patch = models.OneToOneField(Patch, primary_key = True)
    last_modified = models.DateTimeField(default = datetime.datetime.now)
    orig_state = models.ForeignKey(State)

def _patch_change_callback(sender, instance, **kwargs):
    # we only want notification of modified patches
    if instance.pk is None:
        return

    if instance.project is None or not instance.project.send_notifications:
        return

    try:
        orig_patch = Patch.objects.get(pk = instance.pk)
    except Patch.DoesNotExist:
        return

    # If there's no interesting changes, abort without creating the
    # notification
    if orig_patch.state == instance.state:
        return

    notification = None
    try:
        notification = PatchChangeNotification.objects.get(patch = instance)
    except PatchChangeNotification.DoesNotExist:
        pass

    if notification is None:
        notification = PatchChangeNotification(patch = instance,
                                               orig_state = orig_patch.state)

    elif notification.orig_state == instance.state:
        # If we're back at the original state, there is no need to notify
        notification.delete()
        return

    notification.last_modified = datetime.datetime.now()
    notification.save()

models.signals.pre_save.connect(_patch_change_callback, sender = Patch)
