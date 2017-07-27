# Patchwork - automated patch tracking system
# Copyright (C) 2015 Intel Corporation
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

from email.parser import HeaderParser
import sys

from django.core.management.base import BaseCommand
from patchwork.models import Patch, Project
from patchwork.bin.parsemail import find_project


class Command(BaseCommand):
    help = 'Reassign project of patches and series when ' \
           'subject_prefix_tags changes'
    args = 'project'

    def handle(self, *args, **options):

        if len(args) != 1:
            print('error: Need a project.')
            sys.exit(1)

        try:
            project = Project.objects.get(linkname=args[0])
        except Project.DoesNotExist:
            print("error: can't find project '%s'" % args[0])
            sys.exit(1)

        parser = HeaderParser()
        query = Patch.objects.filter(project=project)
        count = query.count()
        for i, patch in enumerate(query.iterator()):
            if (i % 10) == 0:
                sys.stdout.write("%06d/%06d\r" % (i, count))
                sys.stdout.flush()

            headers = parser.parsestr(patch.headers)
            new_project = find_project(headers)
            if new_project == patch.project:
                continue

            patch.project = new_project
            patch.save()
            series = patch.series()
            if not series:
                continue
            series.project = new_project
            series.save()

        sys.stdout.write("%06d/%06d\r" % (count, count))
        sys.stdout.write('\ndone\n')
