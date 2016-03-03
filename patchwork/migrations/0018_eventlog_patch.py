# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0017_series_meta'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventlog',
            name='patch',
            field=models.ForeignKey(to='patchwork.Patch', null=True),
        ),
    ]
