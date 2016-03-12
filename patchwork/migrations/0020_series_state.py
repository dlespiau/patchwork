# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0019_eventlog_patch'),
    ]

    operations = [
        migrations.AddField(
            model_name='seriesrevision',
            name='state',
            field=models.SmallIntegerField(default=0, choices=[(0, b'incomplete'), (1, b'initial'), (2, b'in progress'), (3, b'done')]),
        ),
        migrations.AddField(
            model_name='seriesrevision',
            name='state_summary',
            field=jsonfield.fields.JSONField(null=True),
        ),
    ]
