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

# This file is import from mercurial (tests/test-lock.py) with a few
# modifications to work with patchwork's lock.py version.
#
# The last revision it was synced with is:
# https://selenic.com/hg/rev/e72b62b154b0

from __future__ import absolute_import

import copy
import os
import tempfile
import types
import unittest

from patchwork import lock
from patchwork import lock as error

testlockname = 'testlock'

# work around http://bugs.python.org/issue1515
if types.MethodType not in copy._deepcopy_dispatch:
    def _deepcopy_method(x, memo):
        return type(x)(x.im_func, copy.deepcopy(x.im_self, memo), x.im_class)
    copy._deepcopy_dispatch[types.MethodType] = _deepcopy_method


class lockwrapper(lock.lock):

    def __init__(self, pidoffset, *args, **kwargs):
        # lock.lock.__init__() calls lock(), so the pidoffset assignment needs
        # to be earlier
        self._pidoffset = pidoffset
        super(lockwrapper, self).__init__(*args, **kwargs)

    def _getpid(self):
        return os.getpid() + self._pidoffset


class teststate(object):

    def __init__(self, testcase, dir, pidoffset=0):
        self._testcase = testcase
        self._acquirecalled = False
        self._releasecalled = False
        self._postreleasecalled = False
        self._pidoffset = pidoffset

    def makelock(self, *args, **kwargs):
        l = lockwrapper(self._pidoffset, testlockname,
                        releasefn=self.releasefn, acquirefn=self.acquirefn,
                        *args, **kwargs)
        l.postrelease.append(self.postreleasefn)
        return l

    def acquirefn(self):
        self._acquirecalled = True

    def releasefn(self):
        self._releasecalled = True

    def postreleasefn(self):
        self._postreleasecalled = True

    def assertacquirecalled(self, called):
        self._testcase.assertEqual(
            self._acquirecalled, called,
            'expected acquire to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._acquirecalled),
            ))

    def resetacquirefn(self):
        self._acquirecalled = False

    def assertreleasecalled(self, called):
        self._testcase.assertEqual(
            self._releasecalled, called,
            'expected release to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._releasecalled),
            ))

    def assertpostreleasecalled(self, called):
        self._testcase.assertEqual(
            self._postreleasecalled, called,
            'expected postrelease to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._postreleasecalled),
            ))

    def assertlockexists(self, exists):
        actual = os.path.lexists(testlockname)
        self._testcase.assertEqual(
            actual, exists,
            'expected lock to %s but actually did %s' % (
                self._toexists(exists),
                self._toexists(actual),
            ))

    def _tocalled(self, called):
        if called:
            return 'called'
        else:
            return 'not called'

    def _toexists(self, exists):
        if exists:
            return 'exist'
        else:
            return 'not exist'


class testlock(unittest.TestCase):

    def testlock(self):
        state = teststate(self, tempfile.mkdtemp(dir=os.getcwd()))
        lock = state.makelock()
        state.assertacquirecalled(True)
        lock.release()
        state.assertreleasecalled(True)
        state.assertpostreleasecalled(True)
        state.assertlockexists(False)

    def testrecursivelock(self):
        state = teststate(self, tempfile.mkdtemp(dir=os.getcwd()))
        lock = state.makelock()
        state.assertacquirecalled(True)

        state.resetacquirefn()
        lock.lock()
        # recursive lock should not call acquirefn again
        state.assertacquirecalled(False)

        lock.release()  # brings lock refcount down from 2 to 1
        state.assertreleasecalled(False)
        state.assertpostreleasecalled(False)
        state.assertlockexists(True)

        lock.release()  # releases the lock
        state.assertreleasecalled(True)
        state.assertpostreleasecalled(True)
        state.assertlockexists(False)

    def testlockfork(self):
        state = teststate(self, tempfile.mkdtemp(dir=os.getcwd()))
        lock = state.makelock()
        state.assertacquirecalled(True)

        # fake a fork
        forklock = copy.deepcopy(lock)
        forklock._pidoffset = 1
        forklock.release()
        state.assertreleasecalled(False)
        state.assertpostreleasecalled(False)
        state.assertlockexists(True)

        # release the actual lock
        lock.release()
        state.assertreleasecalled(True)
        state.assertpostreleasecalled(True)
        state.assertlockexists(False)

    def testinheritlock(self):
        d = tempfile.mkdtemp(dir=os.getcwd())
        parentstate = teststate(self, d)
        parentlock = parentstate.makelock()
        parentstate.assertacquirecalled(True)

        # set up lock inheritance
        with parentlock.inherit() as lockname:
            parentstate.assertreleasecalled(True)
            parentstate.assertpostreleasecalled(False)
            parentstate.assertlockexists(True)

            childstate = teststate(self, d, pidoffset=1)
            childlock = childstate.makelock(parentlock=lockname)
            childstate.assertacquirecalled(True)

            childlock.release()
            childstate.assertreleasecalled(True)
            childstate.assertpostreleasecalled(False)
            childstate.assertlockexists(True)

            parentstate.resetacquirefn()

        parentstate.assertacquirecalled(True)

        parentlock.release()
        parentstate.assertreleasecalled(True)
        parentstate.assertpostreleasecalled(True)
        parentstate.assertlockexists(False)

    def testmultilock(self):
        d = tempfile.mkdtemp(dir=os.getcwd())
        state0 = teststate(self, d)
        lock0 = state0.makelock()
        state0.assertacquirecalled(True)

        with lock0.inherit() as lock0name:
            state0.assertreleasecalled(True)
            state0.assertpostreleasecalled(False)
            state0.assertlockexists(True)

            state1 = teststate(self, d, pidoffset=1)
            lock1 = state1.makelock(parentlock=lock0name)
            state1.assertacquirecalled(True)

            # from within lock1, acquire another lock
            with lock1.inherit() as lock1name:
                # since the file on disk is lock0's this should have the same
                # name
                self.assertEqual(lock0name, lock1name)

                state2 = teststate(self, d, pidoffset=2)
                lock2 = state2.makelock(parentlock=lock1name)
                state2.assertacquirecalled(True)

                lock2.release()
                state2.assertreleasecalled(True)
                state2.assertpostreleasecalled(False)
                state2.assertlockexists(True)

                state1.resetacquirefn()

            state1.assertacquirecalled(True)

            lock1.release()
            state1.assertreleasecalled(True)
            state1.assertpostreleasecalled(False)
            state1.assertlockexists(True)

        lock0.release()

    def testinheritlockfork(self):
        d = tempfile.mkdtemp(dir=os.getcwd())
        parentstate = teststate(self, d)
        parentlock = parentstate.makelock()
        parentstate.assertacquirecalled(True)

        # set up lock inheritance
        with parentlock.inherit() as lockname:
            childstate = teststate(self, d, pidoffset=1)
            childlock = childstate.makelock(parentlock=lockname)
            childstate.assertacquirecalled(True)

            # fork the child lock
            forkchildlock = copy.deepcopy(childlock)
            forkchildlock._pidoffset += 1
            forkchildlock.release()
            childstate.assertreleasecalled(False)
            childstate.assertpostreleasecalled(False)
            childstate.assertlockexists(True)

            # release the child lock
            childlock.release()
            childstate.assertreleasecalled(True)
            childstate.assertpostreleasecalled(False)
            childstate.assertlockexists(True)

        parentlock.release()

    def testinheritcheck(self):
        d = tempfile.mkdtemp(dir=os.getcwd())
        state = teststate(self, d)

        def check():
            raise error.LockInheritanceContractViolation('check failed')
        lock = state.makelock(inheritchecker=check)
        state.assertacquirecalled(True)

        def tryinherit():
            with lock.inherit():
                pass

        self.assertRaises(error.LockInheritanceContractViolation, tryinherit)

        lock.release()


if __name__ == '__main__':
    unittest.main(__name__)
