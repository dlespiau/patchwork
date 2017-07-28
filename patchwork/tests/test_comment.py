# Patchwork - automated patch tracking system
# Copyright (C) 2017 Intel Corporation
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

from django.test import TestCase

from patchwork.models import Comment

NOT_TAGS = \
"""
Hey, hi, hello

message

Nonsense-by: zzz
"""

TAGS = \
"""
Reviewed-by: aaa
Fixes: foo
Signed-off-by: bbb
Acked-by: bar
Tested-by: ccc
Nacked-by: baz
Reported-by: ddd
"""


class CommentTest(TestCase):
    def testPatchResponse(self):
        comment = Comment()
        comment.content = NOT_TAGS + TAGS

        reference_tags = TAGS.split()
        actual_tags = comment.patch_responses().split()

        self.assertListEqual(sorted(reference_tags), sorted(actual_tags))
