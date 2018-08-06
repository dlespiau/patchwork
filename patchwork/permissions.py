# Patchwork - automated patch tracking system
# Copyright (C) 2018 Intel Corporation
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

from patchwork.models import Project, Patch, Series


class Can:
    def __init__(self, user):
        self.user = user

    def edit(self, obj):
        if not self.user.is_authenticated():
            return False

        can = self
        if isinstance(obj, Project):
            project = obj
            return (self.user.is_authenticated and
                    project in self.user.profile.maintainer_projects.all())

        if isinstance(obj, Patch):
            patch = obj
            return (self.user.is_authenticated and
                    (patch.submitter.user == self.user or
                     can.edit(patch.project)))

        return False

    def retest(self, obj):
        can = self
        if isinstance(obj, Series):
            series = obj
            return (can.edit(series.project) or
                    series.submitter.user == self.user)

        return False
