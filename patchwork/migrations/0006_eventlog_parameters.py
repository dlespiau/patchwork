# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0005_event_eventlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventlog',
            name='parameters',
            field=jsonfield.fields.JSONField(null=True),
        ),
    ]
