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

from django import forms
from django.contrib import admin

from patchwork.models import (Project, Person, UserProfile, State, Patch,
                              Comment, Bundle, Tag, Test, TestResult,
                              DelegationRule, Series, SeriesRevision)


class DelegationRuleInline(admin.TabularInline):
    model = DelegationRule
    fields = ('path', 'user', 'priority')


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'linkname', 'listid', 'listemail')
    inlines = [
        DelegationRuleInline,
    ]
admin.site.register(Project, ProjectAdmin)


class PersonAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'has_account')
    search_fields = ('name', 'email')

    def has_account(self, person):
        return bool(person.user)

    has_account.boolean = True
    has_account.admin_order_field = 'user'
    has_account.short_description = 'Account'
admin.site.register(Person, PersonAdmin)


class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
admin.site.register(UserProfile, UserProfileAdmin)


class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'action_required')
admin.site.register(State, StateAdmin)


class SeriesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SeriesForm, self).__init__(*args, **kwargs)
        self.fields['last_revision'].queryset = SeriesRevision.objects.filter(
                series=self.instance)


class SeriesAdmin(admin.ModelAdmin):
    form = SeriesForm
    list_display = ('name', 'project', 'submitter', 'reviewer', 'last_updated')
    list_filter = ('project', )
    search_fields = ('name', 'submitter__name', 'submitter__email',
                     'reviewer__first_name', 'reviewer__last_name')
    date_hierarchy = 'submitted'

admin.site.register(Series, SeriesAdmin)


class PatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'submitter', 'project', 'state', 'date',
                    'archived', 'is_pull_request')
    list_filter = ('project', 'state', 'archived')
    search_fields = ('name', 'submitter__name', 'submitter__email')
    date_hierarchy = 'date'

    def is_pull_request(self, patch):
        return bool(patch.pull_url)

    is_pull_request.boolean = True
    is_pull_request.admin_order_field = 'pull_url'
    is_pull_request.short_description = 'Pull'
admin.site.register(Patch, PatchAdmin)


class CommentAdmin(admin.ModelAdmin):
    list_display = ('patch', 'submitter', 'date')
    search_fields = ('patch__name', 'submitter__name', 'submitter__email')
    date_hierarchy = 'date'
admin.site.register(Comment, CommentAdmin)


class TestAdmin(admin.ModelAdmin):
    pass
admin.site.register(Test, TestAdmin)


class TestResultAdmin(admin.ModelAdmin):
    list_display = ('test', 'revision', 'patch', 'user', 'state', 'url',
                    'summary')
    search_fields = ('test__name', 'patch__name', 'revision__series__name',
                     'test__project__name')
    date_hierarchy = 'date'
admin.site.register(TestResult, TestResultAdmin)


class BundleAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'project', 'public')
    list_filter = ('public', 'project')
    search_fields = ('name', 'owner')
admin.site.register(Bundle, BundleAdmin)


class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
admin.site.register(Tag, TagAdmin)
