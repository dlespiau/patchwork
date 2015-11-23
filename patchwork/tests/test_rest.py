# Patchwork - automated patch tracking system
# coding=utf-8
#
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

from django.core import mail
from django.test import Client
import patchwork.tests.test_series as test_series
from patchwork.tests.test_user import TestUser
from patchwork.models import Series, Patch, SeriesRevision, Test, TestResult

import datetime
import hashlib
import json
import re

import dateutil.parser


entry_points = {
    '/': {
        'flags': (),
    },
    '/projects/': {
        'flags': ('is_list',),
    },
    '/projects/%(project_linkname)s/': {
        'flags': (),
    },
    '/projects/%(project_id)s/': {
        'flags': (),
    },
    '/projects/%(project_linkname)s/events/': {
        'flags': ('is_list',),
    },
    '/projects/%(project_id)s/events/': {
        'flags': ('is_list',),
    },
    '/projects/%(project_linkname)s/series/': {
        'flags': ('is_list',),
    },
    '/projects/%(project_id)s/series/': {
        'flags': ('is_list', ),
    },
    '/series/': {
        'flags': ('is_list',),
    },
    '/series/%(series_id)s/': {
        'flags': (),
    },
    '/series/%(series_id)s/revisions/': {
        'flags': ('is_list',),
    },
    '/series/%(series_id)s/revisions/%(version)s/': {
        'flags': (),
    },
    '/series/%(series_id)s/revisions/%(version)s/mbox/': {
        'flags': ('not_json',),
    },
    '/patches/': {
        'flags': ('is_list',),
    },
    '/patches/%(patch_id)s/': {
        'flags': (),
    },
    '/patches/%(patch_id)s/mbox/': {
        'flags': ('not_json',),
    },
}


class APITestBase(test_series.Series0010):

    def setUp(self):
        super(APITestBase, self).setUp()
        self.series = Series.objects.all()[0]
        self.patch = Patch.objects.all()[2]
        self.user = TestUser(username='user')
        self.maintainer = TestUser(username='maintainer')
        self.maintainer.add_to_maintainers(self.project)

    def check_mbox(self, api_url, filename, md5sum):
        response = self.client.get(api_url)
        s = re.search("filename=([\w\.\-_]+)",
                      response["Content-Disposition"]).group(1)
        self.assertEqual(s, filename)

        # With MySQL, primary keys keep growing and so the actual patch ids
        # will depend on the previous tests run. Make sure to canonicalize
        # the mbox file so we can compare md5sums
        content = re.sub('^X-Patchwork-Id: .*$', 'X-Patchwork-Id: 1',
                         response.content, flags=re.M)
        content_hash = hashlib.md5()
        content_hash.update(content)
        self.assertEqual(content_hash.hexdigest(), md5sum)

    def get(self, url, params={}):
        return self.client.get('/api/1.0' + url % {
                'project_id': self.project.pk,
                'project_linkname': self.project.linkname,
                'series_id': self.series.pk,
                'version': 1,
                'patch_id': self.patch.pk,
        }, params)

    def get_json(self, url, params={}):
        return json.loads(self.get(url, params).content)

    # user: a TestUser instance
    def post_json(self, url, data={}, user=None):
        auth_headers = {}
        if user:
            auth_headers['HTTP_AUTHORIZATION'] = user.basic_auth_header()
        response = self.client.post('/api/1.0' + url % {
            'project_id': self.project.pk,
            'project_linkname': self.project.linkname,
            'series_id': self.series.pk,
            'version': 1,
            'patch_id': self.patch.pk,
            }, content_type="application/json", data=json.dumps(data),
            **auth_headers)
        return (response, json.loads(response.content))


class APITest(APITestBase):

    def testEntryPointPresence(self):
        for entry_point in entry_points:
            r = self.get(entry_point)
            self.assertEqual(r.status_code, 200)

    def testList(self):
        for entry_point in entry_points:
            meta = entry_points[entry_point]
            if 'not_json' in meta['flags']:
                continue

            json = self.get_json(entry_point)

            if 'is_list' not in meta['flags']:
                self.assertTrue('count' not in json)
                continue

            self.assertTrue('count' in json)
            self.assertTrue('next' in json)
            self.assertTrue('previous' in json)
            self.assertTrue('results' in json)

    def testRevisionPatchOrdering(self):
        revision = self.get_json('/series/%(series_id)s/revisions/1/')
        self.assertEqual(revision['version'], 1)
        patches = revision['patches']
        self.assertEqual(len(patches), 4)
        i = 1
        for patch_id in patches:
            patch = self.get_json('/patches/%d/' % patch_id)
            self.assertTrue('[%d/4]' % i in patch['name'])
            i += 1

    def testSeriesMbox(self):
        self.check_mbox("/api/1.0/series/%s/revisions/1/mbox/" % self.series.pk,
                        'for_each_-intel_-crtc-v2.mbox',
                        '42e2b2c9eeccf912c998be41683f50d7')

    def testPatchMbox(self):
        self.check_mbox("/api/1.0/patches/%s/mbox/" % self.patch.pk,
                        '3-4-drm-i915-Introduce-a-for_each_crtc-macro.patch',
                        'b951af09618c6360516f16ed97a30753')

    def testSeriesNewRevisionEvent(self):
        # no 'since' parameter
        events = self.get_json('/projects/%(project_id)s/events/')
        self.assertEqual(events['count'], 1)
        event = events['results'][0]
        self.assertEqual(event['parameters']['revision'], 1)

        event_time_str = event['event_time']
        event_time = dateutil.parser.parse(event_time_str)
        before = (event_time - datetime.timedelta(minutes=1)).isoformat()
        after = (event_time + datetime.timedelta(minutes=1)).isoformat()

        # strictly inferior timestamp, should return the event
        events = self.get_json('/projects/%(project_id)s/events/',
                               params={'since': before})
        self.assertEqual(events['count'], 1)
        event = events['results'][0]
        self.assertEqual(event['parameters']['revision'], 1)

        # same timestamp, should return no event
        events = self.get_json('/projects/%(project_id)s/events/',
                               params={'since': event_time_str})
        self.assertEqual(events['count'], 0)

        # strictly superior timestamp, should return no event
        events = self.get_json('/projects/%(project_id)s/events/',
                               params={'since': after})
        self.assertEqual(events['count'], 0)

    def testNumQueries(self):
        # using the related=expand parameter shouldn't make the number of
        # queries explode.
        with self.assertNumQueries(2):
            self.get('/projects/%(project_id)s/series/')
        with self.assertNumQueries(2):
            self.get('/projects/%(project_id)s/series/',
                     params={'related': 'expand'})


class TestResultTest(APITestBase):
    rev_url = '/series/%(series_id)s/revisions/%(version)s/test-results/'
    patch_url = '/patches/%(patch_id)s/test-results/'
    test_urls = (rev_url, patch_url)

    result_url = 'http://example.org/logs/foo.txt'
    result_summary = 'This contains a summary of the test results'

    def _post_result(self, entry, test_name, state, summary=None, url=None):
        data = {
            'test_name': test_name,
            'state': state,
        }
        if summary:
            data['summary'] = summary
        if url:
            data['url'] = url
        return self.post_json(entry, data=data, user=self.maintainer)

    def testNoTestResults(self):
        return
        for url in self.test_urls:
            results = self.get_json(url)
            self.assertEqual(results['count'], 0)

    def testSubmitTestResultAnonymous(self):
        for url in self.test_urls:
            (r, data) = self.post_json(url, data={
                'test_name': 'test/foo',
                'state': 'pending'
            })
            self.assertEqual(r.status_code, 401)
            self.assertEqual(data['detail'],
                             "Authentication credentials were not provided.")

    def testSubmitTestResultWrongPassword(self):
        old_password = self.maintainer.password
        self.maintainer.password = 'notthepassword'
        for url in self.test_urls:
            (r, data) = self.post_json(url, data={
                'test_name': 'test/foo',
                'state': 'pending'
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 401)
            self.assertEqual(data['detail'], "Invalid username/password")
        self.maintainer.password = old_password

    def testSubmitTestResultWrongUsername(self):
        old_username = self.maintainer.username
        self.maintainer.username = 'nottheusername'
        for url in self.test_urls:
            (r, data) = self.post_json(url, data={
                'test_name': 'test/foo',
                'state': 'pending'
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 401)
            self.assertEqual(data['detail'], "Invalid username/password")
        self.maintainer.username = old_username

    def testSubmitTestResultNotMaintainer(self):
        for url in self.test_urls:
            (r, data) = self.post_json(url, data={
                'test_name': 'test/foo',
                'state': 'pending'
            }, user=self.user)
            self.assertEqual(r.status_code, 403)
            self.assertEqual(data['detail'],
                         "You do not have permission to perform this action.")

    def _cleanup_tests(self):
        TestResult.objects.all().delete()
        Test.objects.all().delete()
        mail.outbox = []

    def testInvalidSubmissions(self):
        """test_name and state are required fields"""
        for url in self.test_urls:
            (r, data) = self.post_json(url, data={
                'state': 'pending'
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 400)
            self.assertEqual(data['test_name'], ["This field is required."])

            (r, data) = self.post_json(url, data={
                'test_name': 'test/foo',
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 400)
            self.assertEqual(data['state'], ["This field is required."])

            (r, data) = self.post_json(url, data={
                'test_name': 'test/foo',
                'state': 'invalid',
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 400)
            self.assertEqual(data['state'], ['Select a valid choice. '
                        'invalid is not one of the available choices.'])

    def testSubmitPartialTestResult(self):
        for url in self.test_urls:
            (r, data) = self.post_json(url, data={
                'test_name': 'test/foo',
                'state': 'pending'
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 201)
            self.assertEqual(data['test_name'], 'test/foo')
            self.assertEqual(data['state'], 'pending')

            tests = Test.objects.all()
            self.assertEqual(len(tests), 1)
            test = tests[0]
            self.assertEqual(test.project, self.project)
            self.assertEqual(test.name, 'test/foo')

            results = TestResult.objects.all()
            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result.test, tests[0])
            revision = SeriesRevision.objects.get(series=self.series,
                                                  version=1)
            if url == self.rev_url:
                self.assertEqual(result.revision, revision)
                self.assertEqual(result.patch, None)
            else:
                self.assertEqual(result.revision, None)
                self.assertEqual(result.patch, self.patch)
            self.assertEqual(result.user, self.maintainer.user)
            self.assertEqual(result.state, TestResult.STATE_PENDING)
            self.assertEqual(result.url, None)
            self.assertEqual(result.summary, None)

            self._cleanup_tests()

    def testSubmitFullTestResult(self):
        for url in self.test_urls:
            (r, data) = self.post_json(url, data={
                'test_name': 'test/foo',
                'state': 'pending',
                'url': self.result_url,
                'summary': self.result_summary,
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 201)
            self.assertEqual(data['url'], self.result_url)
            self.assertEqual(data['summary'], self.result_summary)

            results = TestResult.objects.all()
            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result.url, self.result_url)
            self.assertEqual(result.summary, self.result_summary)

            self._cleanup_tests()

    def testUpdateTestResult(self):
        for url in self.test_urls:
            (r, data) = self.post_json(url, data={
                'test_name': 'test/bar',
                'state': 'pending',
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 201)

            self.assertEqual(Test.objects.all().count(), 1)
            results = TestResult.objects.all()
            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result.state, TestResult.STATE_PENDING)
            self.assertEqual(result.url, None)
            self.assertEqual(result.summary, None)

            (r, data) = self.post_json(url, data={
                'test_name': 'test/bar',
                'state': 'success',
                'url': self.result_url,
                'summary': self.result_summary,
            }, user=self.maintainer)
            self.assertEqual(r.status_code, 201)

            self.assertEqual(Test.objects.all().count(), 1)
            results = TestResult.objects.all()
            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result.state, TestResult.STATE_SUCCESS)
            self.assertEqual(result.url, self.result_url)
            self.assertEqual(result.summary, self.result_summary)

            self._cleanup_tests()

    def testNoMailByDefault(self):
        for url in self.test_urls:
            self._post_result(url, 'new test', 'success')
            self.assertEqual(len(mail.outbox), 0)
            self._cleanup_tests()

    def _configure_test(self, url, test_name, recipient, condition):
        """Create test_name and configure it"""
        self._post_result(url, test_name, 'pending')
        tests = Test.objects.all()
        self.assertEqual(len(tests), 1)
        test = tests[0]
        test.mail_recipient = recipient
        test.mail_condition = condition
        test.save()

    def testMailRecipient(self):
        for url in self.test_urls:
            self.assertEqual(len(mail.outbox), 0)

            self._configure_test(url, 'super test',
                    Test.RECIPIENT_SUBMITTER, Test.CONDITION_ALWAYS)
            self._post_result(url, 'super test', 'success')
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.series.submitter.email_name()])
            self.assertEqual(email.cc, [])

            mail.outbox = []

            self._configure_test(url, 'super test',
                    Test.RECIPIENT_MAILING_LIST, Test.CONDITION_ALWAYS)
            self._post_result(url, 'super test', 'success')
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.to, [self.series.submitter.email_name()])
            self.assertEqual(email.cc, [self.project.listemail])

            self._cleanup_tests()

    def testMailCondition(self):
        for url in self.test_urls:
            self.assertEqual(len(mail.outbox), 0)

            self._configure_test(url, 'super test',
                    Test.RECIPIENT_SUBMITTER, Test.CONDITION_ALWAYS)
            self._post_result(url, 'super test', 'success')
            self.assertEqual(len(mail.outbox), 1)
            mail.outbox = []

            self._configure_test(url, 'super test',
                    Test.RECIPIENT_SUBMITTER, Test.CONDITION_ALWAYS)
            self._post_result(url, 'super test', 'pending')
            self.assertEqual(len(mail.outbox), 0)

            self._configure_test(url, 'super test',
                    Test.RECIPIENT_SUBMITTER, Test.CONDITION_ON_FAILURE)
            self._post_result(url, 'super test', 'success')
            self.assertEqual(len(mail.outbox), 0)

            self._configure_test(url, 'super test',
                    Test.RECIPIENT_SUBMITTER, Test.CONDITION_ON_FAILURE)
            self._post_result(url, 'super test', 'pending')
            self.assertEqual(len(mail.outbox), 0)

            self._configure_test(url, 'super test',
                    Test.RECIPIENT_SUBMITTER, Test.CONDITION_ON_FAILURE)
            self._post_result(url, 'super test', 'warning')
            self.assertEqual(len(mail.outbox), 1)
            mail.outbox = []

            self._configure_test(url, 'super test',
                    Test.RECIPIENT_SUBMITTER, Test.CONDITION_ON_FAILURE)
            self._post_result(url, 'super test', 'failure')
            self.assertEqual(len(mail.outbox), 1)
            mail.outbox = []
