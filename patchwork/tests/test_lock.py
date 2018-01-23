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

    def __init__(self, dir, pidoffset=0):
        self._acquirecalled = False
        self._releasecalled = False
        self._postreleasecalled = False
        self._pidoffset = pidoffset

    def makelock(self, *args, **kwargs):
        lw = lockwrapper(self._pidoffset, testlockname,
                         releasefn=self.releasefn, acquirefn=self.acquirefn,
                         *args, **kwargs)
        lw.postrelease.append(self.postreleasefn)
        return lw

    def acquirefn(self):
        self._acquirecalled = True

    def releasefn(self):
        self._releasecalled = True

    def postreleasefn(self):
        self._postreleasecalled = True

    def assertacquirecalled(self, testcase, called):
        testcase.assertEqual(
            self._acquirecalled, called,
            'expected acquire to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._acquirecalled),
            ))

    def resetacquirefn(self):
        self._acquirecalled = False

    def assertreleasecalled(self, testcase, called):
        testcase.assertEqual(
            self._releasecalled, called,
            'expected release to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._releasecalled),
            ))

    def assertpostreleasecalled(self, testcase, called):
        testcase.assertEqual(
            self._postreleasecalled, called,
            'expected postrelease to be %s but was actually %s' % (
                self._tocalled(called),
                self._tocalled(self._postreleasecalled),
            ))

    def assertlockexists(self, testcase, exists):
        actual = os.path.lexists(testlockname)
        testcase.assertEqual(
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
        state = teststate(tempfile.mkdtemp(dir=os.getcwd()))
        lock = state.makelock()
        state.assertacquirecalled(self, True)
        lock.release()
        state.assertreleasecalled(self, True)
        state.assertpostreleasecalled(self, True)
        state.assertlockexists(self, False)

    def testrecursivelock(self):
        state = teststate(tempfile.mkdtemp(dir=os.getcwd()))
        lock = state.makelock()
        state.assertacquirecalled(self, True)

        state.resetacquirefn()
        lock.lock()
        # recursive lock should not call acquirefn again
        state.assertacquirecalled(self, False)

        lock.release()  # brings lock refcount down from 2 to 1
        state.assertreleasecalled(self, False)
        state.assertpostreleasecalled(self, False)
        state.assertlockexists(self, True)

        lock.release()  # releases the lock
        state.assertreleasecalled(self, True)
        state.assertpostreleasecalled(self, True)
        state.assertlockexists(self, False)

    def testlockfork(self):
        state = teststate(tempfile.mkdtemp(dir=os.getcwd()))
        lock = state.makelock()
        state.assertacquirecalled(self, True)

        # fake a fork
        forklock = copy.deepcopy(lock)
        forklock._pidoffset = 1
        forklock.release()
        state.assertreleasecalled(self, False)
        state.assertpostreleasecalled(self, False)
        state.assertlockexists(self, True)

        # release the actual lock
        lock.release()
        state.assertreleasecalled(self, True)
        state.assertpostreleasecalled(self, True)
        state.assertlockexists(self, False)

    def testinheritlock(self):
        d = tempfile.mkdtemp(dir=os.getcwd())
        parentstate = teststate(d)
        parentlock = parentstate.makelock()
        parentstate.assertacquirecalled(self, True)

        # set up lock inheritance
        with parentlock.inherit() as lockname:
            parentstate.assertreleasecalled(self, True)
            parentstate.assertpostreleasecalled(self, False)
            parentstate.assertlockexists(self, True)

            childstate = teststate(d, pidoffset=1)
            childlock = childstate.makelock(parentlock=lockname)
            childstate.assertacquirecalled(self, True)

            childlock.release()
            childstate.assertreleasecalled(self, True)
            childstate.assertpostreleasecalled(self, False)
            childstate.assertlockexists(self, True)

            parentstate.resetacquirefn()

        parentstate.assertacquirecalled(self, True)

        parentlock.release()
        parentstate.assertreleasecalled(self, True)
        parentstate.assertpostreleasecalled(self, True)
        parentstate.assertlockexists(self, False)

    def testmultilock(self):
        d = tempfile.mkdtemp(dir=os.getcwd())
        state0 = teststate(d)
        lock0 = state0.makelock()
        state0.assertacquirecalled(self, True)

        with lock0.inherit() as lock0name:
            state0.assertreleasecalled(self, True)
            state0.assertpostreleasecalled(self, False)
            state0.assertlockexists(self, True)

            state1 = teststate(d, pidoffset=1)
            lock1 = state1.makelock(parentlock=lock0name)
            state1.assertacquirecalled(self, True)

            # from within lock1, acquire another lock
            with lock1.inherit() as lock1name:
                # since the file on disk is lock0's this should have the same
                # name
                self.assertEqual(lock0name, lock1name)

                state2 = teststate(d, pidoffset=2)
                lock2 = state2.makelock(parentlock=lock1name)
                state2.assertacquirecalled(self, True)

                lock2.release()
                state2.assertreleasecalled(self, True)
                state2.assertpostreleasecalled(self, False)
                state2.assertlockexists(self, True)

                state1.resetacquirefn()

            state1.assertacquirecalled(self, True)

            lock1.release()
            state1.assertreleasecalled(self, True)
            state1.assertpostreleasecalled(self, False)
            state1.assertlockexists(self, True)

        lock0.release()

    def testinheritlockfork(self):
        d = tempfile.mkdtemp(dir=os.getcwd())
        parentstate = teststate(d)
        parentlock = parentstate.makelock()
        parentstate.assertacquirecalled(self, True)

        # set up lock inheritance
        with parentlock.inherit() as lockname:
            childstate = teststate(d, pidoffset=1)
            childlock = childstate.makelock(parentlock=lockname)
            childstate.assertacquirecalled(self, True)

            # fork the child lock
            forkchildlock = copy.deepcopy(childlock)
            forkchildlock._pidoffset += 1
            forkchildlock.release()
            childstate.assertreleasecalled(self, False)
            childstate.assertpostreleasecalled(self, False)
            childstate.assertlockexists(self, True)

            # release the child lock
            childlock.release()
            childstate.assertreleasecalled(self, True)
            childstate.assertpostreleasecalled(self, False)
            childstate.assertlockexists(self, True)

        parentlock.release()

    def testinheritcheck(self):
        d = tempfile.mkdtemp(dir=os.getcwd())
        state = teststate(d)

        def check():
            raise error.LockInheritanceContractViolation('check failed')
        lock = state.makelock(inheritchecker=check)
        state.assertacquirecalled(self, True)

        def tryinherit():
            with lock.inherit():
                pass

        self.assertRaises(error.LockInheritanceContractViolation, tryinherit)

        lock.release()


if __name__ == '__main__':
    unittest.main(__name__)
