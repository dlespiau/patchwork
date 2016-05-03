# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0023_fix_test_state_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seriesrevision',
            name='test_state',
            field=models.SmallIntegerField(blank=True, null=True, choices=[(0, b'pending'), (1, b'info'), (2, b'success'), (3, b'warning'), (4, b'failure')]),
        ),
    ]
