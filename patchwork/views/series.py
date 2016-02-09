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

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.views.generic import View
from patchwork.models import Project, Series, SeriesRevision, TestResult

class SeriesListView(View):
    def get(self, request, *args, **kwargs):
        project = get_object_or_404(Project, linkname=kwargs['project'])
        is_editable = 'true' if project.is_editable(request.user) else 'false'
        return render(request, 'patchwork/series-list.html', {
            'project': project,
            'is_editable': is_editable,
            'default_patches_per_page': settings.DEFAULT_PATCHES_PER_PAGE,
        })

class SeriesView(View):
    def get(self, request, *args, **kwargs):
        series = get_object_or_404(Series, pk=kwargs['series'])
        revisions = get_list_or_404(SeriesRevision, series=series)
        for revision in revisions:
            revision.patch_list = revision.ordered_patches().\
                                        select_related('state', 'submitter')
            revision.test_results = TestResult.objects \
                    .filter(revision=revision, patch=None) \
                    .order_by('test__name').select_related('test')

        return render(request, 'patchwork/series.html', {
            'series': series,
            'project': series.project,
            'cover_letter': revision.cover_letter,
            'revisions': revisions,
        })
