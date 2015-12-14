# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patchwork', '0010_test_results_to_cc_list'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testresult',
            name='date',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
