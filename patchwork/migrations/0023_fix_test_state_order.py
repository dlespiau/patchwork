# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0022_add_test_result_state_info'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seriesrevision',
            name='test_state',
            field=models.SmallIntegerField(null=True, choices=[(0, b'pending'), (1, b'info'), (2, b'success'), (3, b'warning'), (4, b'failure')]),
        ),
        migrations.AlterField(
            model_name='testresult',
            name='state',
            field=models.SmallIntegerField(choices=[(0, b'pending'), (1, b'info'), (2, b'success'), (3, b'warning'), (4, b'failure')]),
        ),
    ]
