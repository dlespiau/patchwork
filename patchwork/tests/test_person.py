# Patchwork - automated patch tracking system
# Copyright (C) 2013 Jeremy Kerr <jk@ozlabs.org>
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

from __future__ import absolute_import

import json
from django.test import TestCase
from django.utils.six.moves import map, range

from patchwork.models import Person


class SubmitterCompletionTest(TestCase):

    def setUp(self):
        self.people = [
            Person(name="Test Name", email="test1@example.com"),
            Person(email="test2@example.com"),
        ]
        list(map(lambda p: p.save(), self.people))

    def testNameComplete(self):
        response = self.client.get('/submitter/', {'q': 'name'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Test Name')

    def testEmailComplete(self):
        response = self.client.get('/submitter/', {'q': 'test2'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['email'], 'test2@example.com')

    def testCompleteLimit(self):
        for i in range(3, 10):
            person = Person(email='test%d@example.com' % i)
            person.save()
        response = self.client.get('/submitter/', {'q': 'test', 'l': 5})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertEqual(len(data), 5)


class PersonModelTest(TestCase):

    def testEmailNameQuoted(self):
        p = Person(name="Name, Test", email="test@example.com")
        self.assertEqual(p.email_name(), '"Name, Test" <test@example.com>')
