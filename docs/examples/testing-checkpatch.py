#!/bin/env python2
# coding=utf-8
import fileinput
import json
import mailbox
import os
import re
import requests
import subprocess
import tempfile

# config
PATCHWORK_URL = 'http://patchwork.freedesktop.org'
KERNEL_PATH = '/home/damien/gfx/sources/linux'

API_URL = PATCHWORK_URL + '/api/1.0'


class TestState(object):
    PENDING = 0
    SUCCESS = 1
    WARNING = 2
    FAILURE = 3


class Test(object):
    '''A test on a series.'''

    def __init__(self, series, revision):
        self.series = series
        self.revision = revision
        self.state = TestState.PENDING
        self.summary = ''
        self.url = None

    def merge_patch_result(self, state, summary):
        if state > self.state:
            self.state = state
        self.summary += summary

    def post_result(self):
        state_names = ['pending', 'success', 'warning', 'failure']
        cmd = subprocess.Popen(['git-pw',
                                '-C', KERNEL_PATH,
                                'post-result',
                                str(self.series),
                                '--revision', str(self.revision),
                                self.TEST_NAME,
                                state_names[self.state],
                                '--summary', self.summary])
        cmd.wait()


class CheckpatchTest(Test):
    CHECKPATCH = KERNEL_PATH + '/scripts/checkpatch.pl'
    TEST_NAME = 'UK.CI.checkpatch.pl'
    IGNORE_LIST = ['SPLIT_STRING', 'COMPLEX_MACRO', 'GIT_COMMIT_ID',
                   'COMMIT_LOG_LONG_LINE', 'BLOCK_COMMENT_STYLE',
                   'FILE_PATH_CHANGES']

    def _counts(self, results):
        counts = [0, 0]
        error = re.compile(r'^ERROR:')
        warning = re.compile(r'^WARNING')
        for line in iter(results.splitlines()):
            if error.search(line):
                counts[0] += 1
            elif warning.search(line):
                counts[1] += 1
        return counts

    def _run(self, mail):
        cmd = subprocess.Popen([self.CHECKPATCH,
                                '--mailback', '--no-summary',
                                '--max-line-length=100',
                                '--ignore', ','.join(self.IGNORE_LIST),
                                '-'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
        (stdout, _) = cmd.communicate(input=mail.as_string())
        state = TestState.SUCCESS
        if cmd.returncode != 0:
            (n_errors, n_warnings) = self._counts(stdout)
            if n_errors > 0:
                state = TestState.FAILURE
            elif n_warnings > 0:
                state = TestState.WARNING
        if stdout and len(stdout) > 1:
            stdout = '\n' + stdout + '\n'
        return (state, stdout)

    def process_patch(self, mail):
        (state, stdout) = self._run(mail)
        header = u'  • Testing %s\n' % mail.get('Subject').replace('\n', '')
        self.merge_patch_result(state, header + stdout)


class TestRunner(object):
    def __init__(self, test_class):
        self.test_class = test_class

    def _process_event(self, event):
        # Retrieves the mbox file of a series and run process_patch() for each
        # mail
        (series, revision) = (event['series'], event['parameters']['revision'])
        mbox_url = API_URL + ('/series/%d/revisions/%d/mbox/' %
                              (series, revision))

        print('== Running %s on series %d v%d' % (self.test_class.__name__,
                                                  series, revision))

        test = self.test_class(series, revision)

        r = requests.get(mbox_url)
        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w+') as tmp:
                tmp.write(r.content)
            for mail in mailbox.mbox(path):
                test.process_patch(mail)
        finally:
            os.remove(path)

        test.post_result()

    def run(self):
        # process events from stdin, one at a time
        for line in fileinput.input():
            self._process_event(json.loads(line))


if __name__ == '__main__':
    runner = TestRunner(CheckpatchTest)
    runner.run()
