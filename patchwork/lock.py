# lock.py - simple advisory locking scheme for mercurial
#
# Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
#

# This file has been taken from the mercurial project, the base revision it's
# derived from is:
#     https://selenic.com/hg/rev/e8564e04382d
# A few changes have been made:
#   - revert to not using the vfs object
#   - import a few functions and classes from util.py and error.py

from __future__ import absolute_import

import contextlib
import errno
import os
import socket
import time
import warnings

#
# from error.py
#


class LockError(IOError):

    def __init__(self, errno, strerror, filename, desc):
        IOError.__init__(self, errno, strerror, filename)
        self.desc = desc


class LockHeld(LockError):

    def __init__(self, errno, filename, desc, locker):
        LockError.__init__(self, errno, 'Lock held', filename, desc)
        self.locker = locker


class LockUnavailable(LockError):
    pass

# LockError is for errors while acquiring the lock -- this is unrelated


class LockInheritanceContractViolation(RuntimeError):
    pass

#
# from util.py
#


def testpid(pid):
    '''return False if pid dead, True if running or not sure'''
    if os.sys.platform == 'OpenVMS':
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError as inst:
        return inst.errno != errno.ESRCH


def makelock(info, pathname):
    try:
        return os.symlink(info, pathname)
    except OSError as why:
        if why.errno == errno.EEXIST:
            raise
    except AttributeError:  # no symlink in os
        pass

    ld = os.open(pathname, os.O_CREAT | os.O_WRONLY | os.O_EXCL)
    os.write(ld, info)
    os.close(ld)


def readlock(pathname):
    try:
        return os.readlink(pathname)
    except OSError as why:
        if why.errno not in (errno.EINVAL, errno.ENOSYS):
            raise
    except AttributeError:  # no symlink in os
        pass
    fp = open(pathname)
    r = fp.read()
    fp.close()
    return r

#
# from lock.py
#


class lock(object):
    '''An advisory lock held by one process to control access to a set
    of files.  Non-cooperating processes or incorrectly written scripts
    can ignore Mercurial's locking scheme and stomp all over the
    repository, so don't do that.

    Typically used via localrepository.lock() to lock the repository
    store (.hg/store/) or localrepository.wlock() to lock everything
    else under .hg/.'''

    # lock is symlink on platforms that support it, file on others.

    # symlink is used because create of directory entry and contents
    # are atomic even over nfs.

    # old-style lock: symlink to pid
    # new-style lock: symlink to hostname:pid

    _host = None

    def __init__(self, file, timeout=-1, releasefn=None, acquirefn=None,
                 desc=None, inheritchecker=None, parentlock=None):
        self.f = file
        self.held = 0
        self.timeout = timeout
        self.releasefn = releasefn
        self.acquirefn = acquirefn
        self.desc = desc
        self._inheritchecker = inheritchecker
        self.parentlock = parentlock
        self._parentheld = False
        self._inherited = False
        self.postrelease = []
        self.pid = self._getpid()
        self.delay = self.lock()
        if self.acquirefn:
            self.acquirefn()

    def __del__(self):
        if self.held:
            warnings.warn("use lock.release instead of del lock",
                          category=DeprecationWarning,
                          stacklevel=2)

            # ensure the lock will be removed
            # even if recursive locking did occur
            self.held = 1

        self.release()

    def _getpid(self):
        # wrapper around os.getpid() to make testing easier
        return os.getpid()

    def lock(self):
        timeout = self.timeout
        while True:
            try:
                self._trylock()
                return self.timeout - timeout
            except LockHeld as inst:
                if timeout != 0:
                    time.sleep(1)
                    if timeout > 0:
                        timeout -= 1
                    continue
                raise LockHeld(errno.ETIMEDOUT, inst.filename, self.desc,
                               inst.locker)

    def _trylock(self):
        if self.held:
            self.held += 1
            return
        if lock._host is None:
            lock._host = socket.gethostname()
        lockname = '%s:%s' % (lock._host, self.pid)
        retry = 5
        while not self.held and retry:
            retry -= 1
            try:
                makelock(lockname, self.f)
                self.held = 1
            except (OSError, IOError) as why:
                if why.errno == errno.EEXIST:
                    locker = self._readlock()
                    # special case where a parent process holds the lock -- this
                    # is different from the pid being different because we do
                    # want the unlock and postrelease functions to be called,
                    # but the lockfile to not be removed.
                    if locker == self.parentlock:
                        self._parentheld = True
                        self.held = 1
                        return
                    locker = self._testlock(locker)
                    if locker is not None:
                        raise LockHeld(errno.EAGAIN, self.f, self.desc, locker)
                else:
                    raise LockUnavailable(why.errno, why.strerror,
                                          why.filename, self.desc)

    def _readlock(self):
        """read lock and return its value

        Returns None if no lock exists, pid for old-style locks, and host:pid
        for new-style locks.
        """
        try:
            return readlock(self.f)
        except (OSError, IOError) as why:
            if why.errno == errno.ENOENT:
                return None
            raise

    def _testlock(self, locker):
        if locker is None:
            return None
        try:
            host, pid = locker.split(":", 1)
        except ValueError:
            return locker
        if host != lock._host:
            return locker
        try:
            pid = int(pid)
        except ValueError:
            return locker
        if testpid(pid):
            return locker
        # if locker dead, break lock.  must do this with another lock
        # held, or can race and break valid lock.
        try:
            l = lock(self.f + '.break', timeout=0)
            os.unlink(self.f)
            l.release()
        except LockError:
            return locker

    def testlock(self):
        """return id of locker if lock is valid, else None.

        If old-style lock, we cannot tell what machine locker is on.
        with new-style lock, if locker is on this machine, we can
        see if locker is alive.  If locker is on this machine but
        not alive, we can safely break lock.

        The lock file is only deleted when None is returned.

        """
        locker = self._readlock()
        return self._testlock(locker)

    @contextlib.contextmanager
    def inherit(self):
        """context for the lock to be inherited by a Mercurial subprocess.

        Yields a string that will be recognized by the lock in the subprocess.
        Communicating this string to the subprocess needs to be done separately
        -- typically by an environment variable.
        """
        if not self.held:
            raise LockInheritanceContractViolation(
                'inherit can only be called while lock is held')
        if self._inherited:
            raise error.LockInheritanceContractViolation(
                'inherit cannot be called while lock is already inherited')
        if self._inheritchecker is not None:
            self._inheritchecker()
        if self.releasefn:
            self.releasefn()
        if self._parentheld:
            lockname = self.parentlock
        else:
            lockname = '%s:%s' % (lock._host, self.pid)
        self._inherited = True
        try:
            yield lockname
        finally:
            if self.acquirefn:
                self.acquirefn()
            self._inherited = False

    def release(self):
        """release the lock and execute callback function if any

        If the lock has been acquired multiple times, the actual release is
        delayed to the last release call."""
        if self.held > 1:
            self.held -= 1
        elif self.held == 1:
            self.held = 0
            if self._getpid() != self.pid:
                # we forked, and are not the parent
                return
            try:
                if self.releasefn:
                    self.releasefn()
            finally:
                if not self._parentheld:
                    try:
                        os.unlink(self.f)
                    except OSError:
                        pass
            # The postrelease functions typically assume the lock is not held
            # at all.
            if not self._parentheld:
                for callback in self.postrelease:
                    callback()


def release(*locks):
    for lock in locks:
        if lock is not None:
            lock.release()
