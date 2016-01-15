# Patchwork - automated patch tracking system
# coding=utf-8
#
# Copyright (C) 2014,2015 Intel Corporation
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

try:
    # django 1.8+
    from django.core.exceptions import FieldDoesNotExist
except:
    from django.db.models.fields import FieldDoesNotExist
from django.conf import settings
from django.core import mail
from django.db.models import Q
from django.http import HttpResponse
from patchwork.models import Project, Series, SeriesRevision, Patch, EventLog, \
                             Test, TestResult, TestStates, Person, SERIES_DEFAULT_NAME
from rest_framework import views, viewsets, mixins, generics, filters, \
                           permissions, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, renderer_classes, detail_route
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from patchwork.serializers import ProjectSerializer, SeriesSerializer, \
                                  RevisionSerializer, PatchSerializer, \
                                  EventLogSerializer, TestResultSerializer
from patchwork.views import patch_to_mbox
from patchwork.views.patch import mbox as patch_mbox
import django_filters


API_REVISION = 2

class RelatedOrderingFilter(filters.OrderingFilter):
    """
    Extends OrderingFilter to support ordering by fields in related models.
    """

    def get_ordering(self, request):
        params = super(RelatedOrderingFilter, self).get_ordering(request)
        if params:
            return [param.replace('.', '__') for param in params]

    def is_valid_field(self, model, field):
        components = field.split('__', 1)
        try:
            field, parent_model, direct, m2m = \
                model._meta.get_field_by_name(components[0])

            # foreign key
            if field.rel and len(components) == 2:
                return self.is_valid_field(field.rel.to, components[1])
            return True
        except FieldDoesNotExist:
            return False

    def remove_invalid_fields(self, queryset, ordering, view):
        return [term for term in ordering
                if self.is_valid_field(queryset.model, term.lstrip('-'))]

class MaintainerPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # read only for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # editable for maintainers
        user = request.user
        if not user.is_authenticated():
            return False
        return obj.project.is_editable(user)


class RequestDjangoFilterBackend(filters.DjangoFilterBackend):
    """A DjangoFilterBackend class that also includes the request"""

    def filter_queryset(self, request, queryset, view):
        filter_class = self.get_filter_class(view, queryset)

        if filter_class:
            filter = filter_class(request.QUERY_PARAMS, queryset=queryset)
            filter.request = request
            return filter.qs

        return queryset


class API(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, format=None):
        return Response({ 'revision': API_REVISION })

class ListMixin(object):
    paginate_by = 20
    paginate_by_param = 'perpage'
    max_paginate_by = 100
    filter_backends = (RelatedOrderingFilter, )

class SeriesFilter(django_filters.FilterSet):

    def submitted_since_filter(queryset, date):
        if date:
            queryset = queryset.filter(submitted__gt=date)
        return queryset

    def updated_since_filter(queryset, date):
        if date:
            queryset = queryset.filter(last_updated__gt=date)
        return queryset

    def submitted_before_filter(queryset, date):
        if date:
            queryset = queryset.filter(submitted__lte=date)
        return queryset

    def updated_before_filter(queryset, date):
        if date:
            queryset = queryset.filter(last_updated__lte=date)
        return queryset

    def submitter_filter(self, queryset, submitter):
        try:
            submitter = int(submitter)
            queryset = queryset.filter(submitter=submitter)
        except ValueError:
            if submitter == 'self' and self.request.user.is_authenticated():
                people = Person.objects.filter(user=self.request.user)
                queryset = queryset.filter(submitter__in=people)
        return queryset

    submitted_since = django_filters.CharFilter(action=submitted_since_filter)
    updated_since = django_filters.CharFilter(action=updated_since_filter)
    submitted_before = django_filters.CharFilter(action=submitted_before_filter)
    updated_before = django_filters.CharFilter(action=updated_before_filter)
    submitter = django_filters.MethodFilter(action='submitter_filter')

    class Meta:
        model = Series
        fields = []

class SeriesListMixin(ListMixin):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    select_fields = ('project', 'submitter', 'reviewer')
    filter_backends = (RequestDjangoFilterBackend, RelatedOrderingFilter)
    filter_class = SeriesFilter

class SelectRelatedMixin(object):
    def select_related(self, queryset):
        select_fields = getattr(self, 'select_fields', None)
        if not select_fields:
            return queryset

        related = self.request.QUERY_PARAMS.get('related')
        if not related:
            return queryset

        return queryset.select_related(*select_fields)

def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

class ProjectViewSet(mixins.ListModelMixin, ListMixin, viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def retrieve(self, request, pk=None):
        if is_integer(pk):
            queryset = get_object_or_404(Project, pk=pk)
        else:
            queryset = get_object_or_404(Project, linkname=pk)
        serializer = ProjectSerializer(queryset)
        return Response(serializer.data)

class SeriesListViewSet(mixins.ListModelMixin,
                        SeriesListMixin,
                        SelectRelatedMixin,
                        viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )

    def get_queryset(self):

        pk = self.kwargs['project_pk']
        if is_integer(pk):
            queryset = self.queryset.filter(project__pk=pk)
        else:
            queryset = self.queryset.filter(project__linkname=pk)
        return self.select_related(queryset)

class SeriesViewSet(mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    SeriesListMixin,
                    viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = Series.objects.all()

def series_mbox(revision):
    patches = revision.ordered_patches()
    data = '\n'.join([patch_to_mbox(x).as_string(True) for x in patches])
    response = HttpResponse(content_type="text/plain")
    response.write(data)
    response['Content-Disposition'] = 'attachment; filename=' + \
        revision.series.filename()
    return response

class RevisionViewSet(mixins.ListModelMixin, ListMixin,
                      viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = SeriesRevision.objects.all()
    serializer_class = RevisionSerializer

    def get_queryset(self):
        series_pk = self.kwargs['series_pk']
        return self.queryset.filter(series=series_pk)

    def retrieve(self, request, series_pk=None, pk=None):
        rev = get_object_or_404(SeriesRevision, series=series_pk, version=pk)
        serializer = RevisionSerializer(rev,
                                        context=self.get_serializer_context())
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def mbox(self, request, series_pk=None, pk=None):
        rev = get_object_or_404(SeriesRevision, series=series_pk, version=pk)
        return series_mbox(rev)

class ResultMixin(object):
    def _object_name(self, obj):
        if isinstance(obj, SeriesRevision):
            name = obj.series.name
            if name == SERIES_DEFAULT_NAME:
                name = "series starting with " + obj.ordered_patches()[0].name
            if obj.version > 1:
                name += " (rev%d)" % obj.version
            return name
        return obj.name

    def _prepare_mail(self, result, obj):
        if result.state == TestResult.STATE_SUCCESS:
            tick = u"✓"
        else:
            tick = u"✗"
        subject = tick + u" %s: %s for %s" % (result.test.name,
                                              result.get_state_display(),
                                              self._object_name(obj))
        body = ''
        if result.summary:
            body += "== Summary ==\n\n"
            body += result.summary
            if body.endswith('\n'):
                body += "\n"
            else:
                body += "\n\n"
        if result.url:
            body += "== Logs ==\n\n"
            body += "For more details see: " + result.url
            body += "\n"

        return (subject, body)

    def _get_msgid(self, obj):
        try:
            return getattr(obj, 'root_msgid')
        except AttributeError:
            return getattr(obj, 'msgid')


    def handle_test_results(self, request, obj, check_obj, q, ctx):
        # auth
        if not 'test_name' in request.DATA:
            return Response({'test_name': ['This field is required.', ]},
                            status=status.HTTP_400_BAD_REQUEST)

        self.check_object_permissions(request, check_obj)

        # update test result and prepare the JSON response
        try:
            test = request.DATA['test_name']
            instance = TestResult.objects.get(q, test__name=test)
        except TestResult.DoesNotExist:
            instance = None

        ctx.update({
            'project': check_obj.project,
            'user': request.user,
        })
        result = TestResultSerializer(instance, data=request.DATA, context=ctx)
        if not result.is_valid():
            return Response(result.errors, status=status.HTTP_400_BAD_REQUEST)

        instance = result.save()

        # mailing, done synchronously with the request, for now
        to = []
        cc = []
        if instance.test.mail_recipient == Test.RECIPIENT_SUBMITTER:
            to.append(check_obj.submitter.email_name())
        elif instance.test.mail_recipient == Test.RECIPIENT_MAILING_LIST:
            to.append(check_obj.submitter.email_name())
            cc.append(check_obj.project.listemail)

        if instance.test.mail_recipient != Test.RECIPIENT_NONE and \
           (instance.test.mail_to_list or instance.test.mail_cc_list):
            to += instance.test.get_to_list()
            cc += instance.test.get_cc_list()

        if to:
            # never send mail on pending
            if instance.state == TestResult.STATE_PENDING:
                to = []

            if (instance.test.mail_condition == Test.CONDITION_ON_FAILURE and
                instance.state not in (TestResult.STATE_WARNING,
                                       TestResult.STATE_FAILURE)):
                to = []

        if to:
            subject, body = self._prepare_mail(instance, obj)
            msgid = self._get_msgid(obj)
            headers = {
                'X-Patchwork-Hint': 'ignore',
                'References': msgid,
                'In-Reply-To': msgid,
            }
            email = mail.EmailMessage(subject, body,
                                      settings.DEFAULT_FROM_EMAIL,
                                      to=to, cc=cc, headers=headers)
            email.send()

        return Response(result.data, status=status.HTTP_201_CREATED)

class RevisionResultViewSet(viewsets.ViewSet, ResultMixin):
    permission_classes = (MaintainerPermission, )
    authentication_classes = (BasicAuthentication, )

    # update the status of the series
    def update_series_status(self, series):
        # Series.object.filter()
        if isinstance(series, SeriesRevision): 
            # find all test for the latest revision
            testResults = TestResult.objects.filter(revision=series)
            if testResults.count() == 0:
                series.test_state = TestStates.STATE_PENDING
            else:
                series.test_state = max([tr.state for tr in testResults if tr])
            series.save()

    def create(self, request, series_pk, version_pk):
        rev = get_object_or_404(SeriesRevision, series=series_pk,
                                version=version_pk)
        result = self.handle_test_results(request, rev, rev.series,
                                        Q(revision=rev), {'revision': rev})

        if result.status_code != status.HTTP_400_BAD_REQUEST:
            self.update_series_status(rev)

        return result

def endpoint(endpoint):
    """Used to rename a method on a ViewSet"""

    def decorator(func):
        func.endpoint = endpoint
        return func
    return decorator

class PatchViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   ListMixin, ResultMixin,
                   viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = Patch.objects.all()
    serializer_class = PatchSerializer

    @detail_route(methods=['get'])
    def mbox(self, request, pk=None):
        return patch_mbox(request, pk)

class PatchResultViewSet(viewsets.ViewSet, ResultMixin):
    permission_classes = (MaintainerPermission, )
    authentication_classes = (BasicAuthentication, )

    def create(self, request, patch_pk=None):
        patch = get_object_or_404(Patch, pk=patch_pk)
        return self.handle_test_results(request, patch, patch, Q(patch=patch),
                                        {'patch': patch})

class EventTimeFilter(django_filters.FilterSet):

    def event_time_filter(query_set, date):
        queryset = query_set
        if date:
            queryset =  queryset.filter(event_time__gt=date)
        return queryset

    since = django_filters.CharFilter(name='event_time', action=event_time_filter)

    class Meta:
        model = EventLog
        fields = ['since']

class EventLogViewSet(mixins.ListModelMixin,
                      ListMixin,
                      viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = EventLog.objects.all().select_related('event')
    serializer_class = EventLogSerializer
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter)
    filter_class = EventTimeFilter

    def get_queryset(self):

        pk = self.kwargs['project_pk']
        if is_integer(pk):
            queryset = self.queryset.filter(series__project__pk=pk)
        else:
            queryset = self.queryset.filter(series__project__linkname=pk)
        return queryset
