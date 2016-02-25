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

import json

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from patchwork.models import Project, Series, SeriesRevision, Patch, Person, \
    State, EventLog, Test, TestResult, TestState, APIToken
from rest_framework import serializers
from rest_framework import fields
from enum import Enum


class RelatedMode(Enum):
    """Select how to show related fields in the JSON responses."""
    primary_key = 1
    expand = 2


class Iso8601DateTimeField(fields.DateTimeField):

    def __init__(self, **kwargs):
        super(Iso8601DateTimeField, self).__init__(format='iso-8601', **kwargs)


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

        # All DateTimeFields should be in ISO 8601 format so nano seconds
        # aren't truncated. This is important to be able to correctly re-inject
        # the timestamps string the API gives you back into queries and have
        # the gt (greater than) and gte (greater or equal) operators work
        # correctly.
        self.field_mapping[models.DateTimeField] = Iso8601DateTimeField

        self._pw_related = RelatedMode.primary_key
        related = None
        if 'request' in self.context:
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

# See https://github.com/tomchristie/django-rest-framework/issues/1880


class JSONField(serializers.WritableField):

    def to_native(self, obj):
        return obj

    def from_native(self, value):
        if value is not None and not isinstance(value, dict):
            raise ValidationError("This field must be a JSON object")

        return value


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'name')


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
    version = serializers.SerializerMethodField('get_version')
    n_patches = serializers.SerializerMethodField('get_n_patches')
    test_state = serializers.SerializerMethodField('get_test_state')

    def get_version(self, obj):
        if not obj.last_revision:
            return 1
        return obj.last_revision.version

    def get_n_patches(self, obj):
        if not obj.last_revision:
            return 0
        return obj.last_revision.n_patches

    def get_test_state(self, obj):
        if not obj.last_revision:
            return None
        state = obj.last_revision.test_state
        if state is not None:
            return dict(TestState.STATE_CHOICES)[state]
        return state

    class Meta:
        model = Series
        fields = ('id', 'project', 'name', 'n_patches', 'submitter',
                  'submitted', 'last_updated', 'version', 'reviewer',
                  'test_state')
        read_only_fields = ('project', 'submitter', 'submitted',
                            'last_updated')
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
    patches = serializers.SerializerMethodField('get_patches')

    def get_patches(self, revision):
        queryset = revision.ordered_patches()

        if self._pw_related == RelatedMode.expand:
            serializer = PatchSerializer(instance=queryset, many=True,
                                         context=self.context)
            return serializer.data

        return [patch.pk for patch in queryset]

    class Meta:
        model = SeriesRevision
        fields = ('version', 'cover_letter', 'patches')
        read_only_fields = ('version', 'cover_letter')
        expand_serializers = {
            'patches': PatchSerializer,
        }


class EventLogSerializer(PatchworkModelSerializer):
    name = serializers.CharField(source='event.name', read_only=True)
    parameters = JSONField(read_only=True)

    class Meta:
        model = EventLog
        fields = ('name', 'event_time', 'series', 'user', 'parameters')
        expand_serializers = {
            'series': SeriesSerializer,
            'user': UserSerializer,
        }


class ValueChoiceField(serializers.ChoiceField):

    def to_native(self, value):
        for k, v in self.choices:
            if value == k:
                return v

    def from_native(self, value):
        for k, v in self.choices:
            if value == v:
                return k
        msg = self.error_messages['invalid_choice'] % {'value': value}
        raise ValidationError(msg)


class TestResultSerializer(serializers.Serializer):
    test_name = serializers.CharField(source='test.name')
    state = ValueChoiceField(choices=TestState.STATE_CHOICES)
    url = serializers.URLField(required=False, allow_none=True)
    summary = serializers.CharField(required=False, allow_none=True)

    def resolve_fields(self, validated_data):
        project = self.context['project']
        assert project
        user = self.context['user']
        assert user

        test_name = validated_data.pop('test.name')
        test, _ = Test.objects.get_or_create(project=project, name=test_name)
        validated_data['test'] = test
        validated_data['user'] = user
        validated_data['revision'] = self.context.get('revision', None)
        validated_data['patch'] = self.context.get('patch', None)

    def create(self, validated_data):
        self.resolve_fields(validated_data)
        return TestResult.objects.create(**validated_data)

    def update(self, instance, validated_data):
        self.resolve_fields(validated_data)
        instance.test = validated_data.get('test', instance.test)
        instance.state = validated_data.get('state', instance.state)
        instance.url = validated_data.get('url', instance.url)
        instance.summary = validated_data.get('summary', instance.summary)
        instance.save()
        return instance

    def restore_object(self, validated_data, instance=None):
        if instance:
            return self.update(instance, validated_data)
        return self.create(validated_data)

class APITokenSerializer(PatchworkModelSerializer):
    parameters = JSONField(read_only=True)
    class Meta:
        model = APIToken
        fields = ('id', 'name', 'user', 'state', 'created')
        read_only_fields = ('id', 'created', 'user')
        expand_serializers = {
            'user': UserSerializer
        }

    def validate_name(self, data, field):
        name = data['name']
        user = self.context['request'].user
        if APIToken.objects.filter(name=name,user=user).count():
            raise serializers.ValidationError("Name exists")
        return data

