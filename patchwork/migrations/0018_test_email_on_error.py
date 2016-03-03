# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0017_series_meta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='test',
            name='mail_condition',
            field=models.SmallIntegerField(default=0, choices=[(0, b'always'), (1, b'on warning/failure'), (2, b'on failure')]),
        ),
    ]
