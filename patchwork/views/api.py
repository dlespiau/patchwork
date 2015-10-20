# Patchwork - automated patch tracking system
# Copyright (C) 2014 Intel Corporation
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

from patchwork.models import Project, Series, SeriesRevision, Patch, EventLog
from rest_framework import views, viewsets, mixins, generics, filters, permissions
from rest_framework.decorators import api_view, renderer_classes, \
                                      permission_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from patchwork.serializers import ProjectSerializer, SeriesSerializer, \
                                  RevisionSerializer, PatchSerializer, \
                                  EventLogSerializer


API_REVISION = 1

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

class API(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, format=None):
        return Response({ 'revision': API_REVISION })

class ListMixin(object):
    paginate_by = 20
    paginate_by_param = 'perpage'
    max_paginate_by = 100

class SeriesListMixin(ListMixin):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    filter_backends = (filters.OrderingFilter, )
    ordering_fields = ('name', 'n_patches', 'submitter__name', 'reviewer__name',
                        'submitted', 'last_updated')

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
                        viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )

    def get_queryset(self):

        pk = self.kwargs['project_pk']
        if is_integer(pk):
            queryset = self.queryset.filter(project__pk=pk)
        else:
            queryset = self.queryset.filter(project__linkname=pk)
        return queryset

class SeriesViewSet(mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    SeriesListMixin,
                    viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = Series.objects.all()

class RevisionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = SeriesRevision.objects.all()
    serializer_class = RevisionSerializer

    def get_queryset(self):

        series_pk = self.kwargs['series_pk']
        return self.queryset.filter(series=series_pk)

    def retrieve(self, request, series_pk=None, pk=None):
        rev = get_object_or_404(SeriesRevision, series=series_pk, version=pk)
        print(self.get_serializer_context())
        serializer = RevisionSerializer(rev,
                                        context=self.get_serializer_context())
        return Response(serializer.data)

class PatchViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   ListMixin,
                   viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = Patch.objects.all()
    serializer_class = PatchSerializer

class EventLogViewSet(mixins.ListModelMixin,
                      ListMixin,
                      viewsets.GenericViewSet):
    permission_classes = (MaintainerPermission, )
    queryset = EventLog.objects.all()
    serializer_class = EventLogSerializer

    def get_queryset(self):

        pk = self.kwargs['project_pk']
        if is_integer(pk):
            queryset = self.queryset.filter(series__project__pk=pk)
        else:
            queryset = self.queryset.filter(series__project__linkname=pk)
        return queryset
