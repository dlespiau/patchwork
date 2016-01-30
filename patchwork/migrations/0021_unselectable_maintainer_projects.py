# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0020_series_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='maintainer_projects',
            field=models.ManyToManyField(related_name='maintainer_project', to='patchwork.Project', blank=True),
        ),
    ]
