# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0012_project_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='seriesrevision',
            name='test_state',
            field=models.SmallIntegerField(default=0, choices=[(0, b'pending'), (1, b'success'), (2, b'warning'), (3, b'failure')]),
        ),
    ]
