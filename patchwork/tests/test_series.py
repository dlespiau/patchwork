# Patchwork - automated patch tracking system
# Copyright (C) 2014 Intel Corporation
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

import os

from django.test import TestCase
from patchwork.models import Patch, Series, SeriesRevision, Project, \
                             SERIES_DEFAULT_NAME
from patchwork.tests.utils import read_mail
from patchwork.tests.utils import defaults, read_mail, TestSeries

from patchwork.bin.parsemail import parse_mail

class SeriesTest(TestCase):
    fixtures = ['default_states']

    def setUp(self):
        self.assertTrue(self.project is not None)
        self.project.save()

        # insert the mails. 'mails' is an optional field, for subclasses
        # that do have a list of on-disk emails.
        if hasattr(self, 'mails'):
            self.n_mails = len(self.mails)
            for filename in self.mails:
                mail = read_mail(os.path.join('series', filename))
                parse_mail(mail)

    def commonInsertionChecks(self):
        # subclasses are responsible for defining those variables
        self.assertTrue(self.n_patches is not None)
        self.assertTrue(self.root_msgid is not None)
        self.assertTrue(self.series_name is not None)

        # make sure the series has been correctly populated
        series = Series.objects.all()
        self.assertEquals(series.count(), 1)

        s = series[0]
        self.assertEquals(s.project, self.project)
        self.assertEquals(s.name, self.series_name)

        # same thing for the revision
        revisions = SeriesRevision.objects.all()
        self.assertEquals(revisions.count(), 1)

        r = revisions[0]
        self.assertEquals(r.series_id, s.id)
        self.assertEquals(r.root_msgid, self.root_msgid)
        self.assertEquals(r.cover_letter, self.cover_letter)

        # and list of patches
        r_patches = r.patches.all()
        self.assertEquals(r_patches.count(), self.n_patches)

        # Make sure we also insert patches. Most thorough checks on patches
        # isn't the subject here.
        patches = Patch.objects.all()
        self.assertEquals(patches.count(), self.n_patches)

class GeneratedSeriesTest(SeriesTest):
    project = defaults.project

    def _create_series(self, n_patches, has_cover_letter=True):
        self.n_patches = n_patches
        series = TestSeries(self.n_patches, has_cover_letter)
        mails = series.create_mails()
        self.root_msgid = mails[0].get('Message-Id')
        self.has_cover_letter = has_cover_letter
        if has_cover_letter:
            self.series_name = defaults.series_name
            self.cover_letter = defaults.series_cover_letter
        else:
            self.series_name = SERIES_DEFAULT_NAME
            self.cover_letter = None
        return (series, mails)

class BasicGeneratedSeriesTests(GeneratedSeriesTest):
    def testInsertion(self):
        (series, mails) = self._create_series(3)
        series.insert(mails)
        self.commonInsertionChecks()

    def testInsertionNoCoverLetter(self):
        (series, mails) = self._create_series(3, has_cover_letter=False)
        series.insert(mails)
        self.commonInsertionChecks()

class IntelGfxTest(SeriesTest):
    project = Project(linkname = 'intel-gfx',
                      name = 'Intel Gfx',
                      listid = 'intel-gfx.lists.freedesktop.org',
                      listemail='intel-gfx@lists.freedesktop.org')

class SingleMailSeries(IntelGfxTest):
    mails = (
        '0001-single-mail.mbox',
    )
    n_patches = 1
    series_name = "drm/i915: Hold CRTC lock whilst freezing the planes"

    root_msgid = '<1400748280-26449-1-git-send-email-chris@chris-wilson.co.uk>'
    cover_letter = None

    def testInsertion(self):
        """A single patch is a series of 1 patch"""

        self.commonInsertionChecks()

        # make sure we got the right patch inserted as well
        patches = Patch.objects.all()
        patch = patches[0]
        self.assertEquals(patch.msgid, self.root_msgid)

class Series0010(IntelGfxTest):
    mails = (
        '0010-multiple-mails-cover-letter.mbox',
        '0011-multiple-mails-cover-letter.mbox',
        '0012-multiple-mails-cover-letter.mbox',
        '0013-multiple-mails-cover-letter.mbox',
        '0014-multiple-mails-cover-letter.mbox',
    )
    n_patches = 4
    series_name = "for_each_{intel_,}crtc v2"

    root_msgid = '<1400020344-17248-1-git-send-email-damien.lespiau@intel.com>'

    cover_letter = \
"""With Daniel's help to figure out an arcane corner of coccinelle, here is v2 of
a series introducing macros to iterate through the CRTCs instead of using
list_for_each_entry() and mode_config.crtc_list, a tiny bit more readable and
easier to recall.

Damien Lespiau (4):
  drm/i915: Introduce a for_each_intel_crtc() macro
  drm/i915: Use for_each_intel_crtc() when iterating through intel_crtcs
  drm/i915: Introduce a for_each_crtc() macro
  drm/i915: Use for_each_crtc() when iterating through the CRTCs

 drivers/gpu/drm/i915/i915_debugfs.c  |  4 +-
 drivers/gpu/drm/i915/i915_drv.c      |  2 +-
 drivers/gpu/drm/i915/i915_drv.h      |  6 +++
 drivers/gpu/drm/i915/intel_display.c | 71 +++++++++++++++---------------------
 drivers/gpu/drm/i915/intel_fbdev.c   |  6 +--
 drivers/gpu/drm/i915/intel_pm.c      | 12 +++---
 6 files changed, 47 insertions(+), 54 deletions(-)"""

class MultipleMailCoverLetterSeries(Series0010):
    def testInsertion(self):
        """A series with a cover letter and 4 patches"""

        self.commonInsertionChecks()

class MultipleMailCoverLetterSeriesUnordered(Series0010):
    mails = (
        '0013-multiple-mails-cover-letter.mbox',
        '0012-multiple-mails-cover-letter.mbox',
        '0010-multiple-mails-cover-letter.mbox',
        '0011-multiple-mails-cover-letter.mbox',
        '0014-multiple-mails-cover-letter.mbox',
    )

    def testInsertion(self):
        """A series with a cover letter and 4 patches, receiving emails in
           a different order than the 'natural' one, ie not starting by
           the cover letter"""

        self.commonInsertionChecks()

class Series0020(IntelGfxTest):
    mails = (
        '0020-multiple-mails-no-cover-letter.mbox',
        '0021-multiple-mails-no-cover-letter.mbox',
        '0022-multiple-mails-no-cover-letter.mbox',
    )
    n_patches = 3
    series_name = SERIES_DEFAULT_NAME

    root_msgid = '<1421182013-751-1-git-send-email-kenneth@whitecape.org>'
    cover_letter = None

class MultipleMailNoCoverLetterSeries(Series0020):
    def testInsertion(self):
        """A series with 3 patches, but no cover letter"""

        self.commonInsertionChecks()
