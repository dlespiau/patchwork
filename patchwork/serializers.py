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

from django.contrib.auth.models import User
from patchwork.models import Project, Series, SeriesRevision, Patch, Person, \
                             State, EventLog
from rest_framework import serializers
from enum import Enum

class RelatedMode(Enum):
    """Select how to show related fields in the JSON responses."""
    primary_key = 1
    expand = 2

class PatchworkModelSerializerOptions(serializers.ModelSerializerOptions):
    """Meta class options for PatchworkModelSerializer"""
    def __init__(self, meta):
        super(PatchworkModelSerializerOptions, self).__init__(meta)
        self.expand_serializers = getattr(meta, 'expand_serializers', {})

class PatchworkModelSerializer(serializers.ModelSerializer):
    """A model serializer with configurable related fields.

       PatchworkModelSerializer can either show related fields as a integer
       or expand them to include the related full JSON object.
       This behaviour is selectable through the 'related' GET parameter. Adding
       'related=expand' to the GET request will expand related fields.
    """

    _options_class = PatchworkModelSerializerOptions

    def __init__(self, *args, **kwargs):
        super(PatchworkModelSerializer, self).__init__(*args, **kwargs)

        self._pw_related = RelatedMode.primary_key
        related = self.context['request'].QUERY_PARAMS.get('related')
        if not related:
            return

        try:
            self._pw_related = RelatedMode[related]
        except KeyError:
            pass

    def _pw_get_nested_field(self, model_field, related_model, to_many):
        class NestedModelSerializer(serializers.ModelSerializer):
            class Meta:
                model = related_model

        if model_field.name in self.opts.expand_serializers:
            serializer_class = self.opts.expand_serializers[model_field.name]
            return serializer_class(context=self.context, many=to_many)
        return NestedModelSerializer(many=to_many)

    def get_related_field(self, model_field, related_model, to_many):
        if self._pw_related == RelatedMode.expand:
            return self._pw_get_nested_field(model_field, related_model, to_many)
        else:
            return super(PatchworkModelSerializer, self). \
                    get_related_field(model_field, related_model, to_many)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', )

class PersonSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='display_name', read_only=True)
    class Meta:
        model = Person
        fields = ('id', 'name', )

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('id', 'name', 'linkname', 'listemail', 'web_url', 'scm_url',
                  'webscm_url')

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ('id', 'name')

class SeriesSerializer(PatchworkModelSerializer):
    class Meta:
        model = Series
        fields = ('id', 'project', 'name', 'n_patches', 'submitter',
                  'submitted', 'last_updated', 'version', 'reviewer')
        read_only_fields = ('project', 'n_patches', 'submitter', 'submitted',
                            'last_updated', 'version')
        expand_serializers = {
            'project': ProjectSerializer,
            'submitter': PersonSerializer,
            'reviewer': UserSerializer,
        }

class PatchSerializer(PatchworkModelSerializer):
    class Meta:
        model = Patch
        fields = ('id', 'project', 'name', 'date', 'submitter', 'state',
                  'content')
        read_only_fields = ('id', 'project', 'name', 'date', 'submitter',
                            'content')
        expand_serializers = {
            'project': ProjectSerializer,
            'submitter': PersonSerializer,
            'state': StateSerializer,
        }

class RevisionSerializer(PatchworkModelSerializer):
    class Meta:
        model = SeriesRevision
        fields = ('version', 'cover_letter', 'patches')
        read_only_fields = ('version', 'cover_letter')
        expand_serializers = {
            'patches': PatchSerializer,
        }

class EventLogSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='event.name', read_only=True)
    class Meta:
        model = EventLog
        fields = ('name', 'event_time', 'series', 'user')
