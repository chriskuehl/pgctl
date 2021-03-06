# pylint:disable=no-self-use, unused-argument
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
from subprocess import check_call
from subprocess import PIPE
from subprocess import Popen

from pytest import yield_fixture as fixture
from testing import run

from pgctl.cli import svstat


class DescribeDateExample(object):

    @fixture
    def service_name(self):
        yield 'date'

    def it_does_start(self, in_example_dir):
        assert not os.path.isfile('now.date')
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            assert os.path.isfile('now.date')
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))


class DescribeTailExample(object):

    @fixture
    def service_name(self):
        yield 'tail'

    def it_does_start(self, in_example_dir):
        test_string = 'oh, hi there.\n'
        with open('input', 'w') as input:
            input.write(test_string)
        assert not os.path.isfile('output')

        check_call(('pgctl-2015', 'start', 'tail'))
        try:
            assert os.path.isfile('output')
            assert open('output').read() == test_string
        finally:
            check_call(('pgctl-2015', 'stop', 'tail'))


class DescribeStart(object):

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'start', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert stderr == (
            "Starting: ('unknown',)\n"
            "No such playground service: 'unknown'\n"
        )
        assert p.returncode == 1

    def it_is_idempotent(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        try:
            check_call(('pgctl-2015', 'start', 'date'))
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))


class DescribeStop(object):

    def it_does_stop(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        check_call(('pgctl-2015', 'stop', 'date'))

        assert svstat('playground/date') == ['down']

    def it_is_successful_before_start(self, in_example_dir):
        check_call(('pgctl-2015', 'stop', 'date'))

    def it_fails_given_unknown(self, in_example_dir):
        p = Popen(('pgctl-2015', 'stop', 'unknown'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert stderr == (
            "Stopping: ('unknown',)\n"
            "No such playground service: 'unknown'\n"
        )
        assert p.returncode == 1


def pty_normalize_newlines(fd):
    r"""
    Twiddle the tty flags such that \n won't get munged to \r\n.
    Details:
        https://docs.python.org/2/library/termios.html
        http://ftp.gnu.org/old-gnu/Manuals/glibc-2.2.3/html_chapter/libc_17.html#SEC362
    """
    import termios as T
    attrs = T.tcgetattr(fd)
    attrs[1] &= ~(T.ONLCR | T.OPOST)
    T.tcsetattr(fd, T.TCSANOW, attrs)


class DescribeDebug(object):

    @fixture
    def service_name(self):
        yield 'greeter'

    def read_line(self, fd):
        # read one-byte-at-a-time to avoid deadlocking by reading too much
        line = ''
        byte = None
        while byte not in ('\n', ''):
            byte = os.read(fd, 1).decode('utf-8')
            line += byte
        return line

    def assert_works_interactively(self):
        read, write = os.openpty()
        pty_normalize_newlines(read)
        proc = Popen(('pgctl-2015', 'debug', 'greeter'), stdin=PIPE, stdout=write)
        os.close(write)

        try:
            assert self.read_line(read) == 'What is your name?\n'
            proc.stdin.write('Buck\n')
            assert self.read_line(read) == 'Hello, Buck.\n'

            # the service should re-start
            assert self.read_line(read) == 'What is your name?\n'
        finally:
            proc.kill()

    def it_works_with_nothing_running(self, in_example_dir):
        assert svstat('playground/greeter') == ['unsupervised']
        self.assert_works_interactively()

    def it_fails_with_multiple_services(self, in_example_dir):
        p = Popen(('pgctl-2015', 'debug', 'abc', 'def'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stdout == ''
        assert stderr == (
            'Must debug exactly one service, not: abc, def\n'
        )
        assert p.returncode == 1

    def it_first_stops_the_background_service_if_running(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'greeter'))
        assert svstat('playground/greeter') == ['up']

        self.assert_works_interactively()


class DescribeRestart(object):

    def it_is_just_stop_then_start(self, in_example_dir):
        p = Popen(('pgctl-2015', 'restart', 'date'), stdout=PIPE, stderr=PIPE)
        stdout, stderr = run(p)
        assert stderr == '''\
Stopping: ('date',)
Stopped: ('date',)
Starting: ('date',)
Started: ('date',)
'''
        assert stdout == ''
        assert p.returncode == 0
        assert svstat('playground/date') == ['up']

    def it_also_works_when_up(self, in_example_dir):
        check_call(('pgctl-2015', 'start', 'date'))
        assert svstat('playground/date') == ['up']

        self.it_is_just_stop_then_start(in_example_dir)


class DescribeStartMultipleServices(object):

    @fixture
    def service_name(self):
        yield 'multiple'

    def it_only_starts_the_indicated_services(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start', 'date'))

            assert svstat('playground/date') == ['up']
            assert svstat('playground/tail') == ['down']
        finally:
            check_call(('pgctl-2015', 'stop', 'date'))

    def it_starts_multiple_services(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start', 'date', 'tail'))

            assert svstat('playground/date') == ['up']
            assert svstat('playground/tail') == ['up']
        finally:
            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

    def it_stops_multiple_services(self, in_example_dir):
        try:
            check_call(('pgctl-2015', 'start', 'date', 'tail'))

            assert svstat('playground/date') == ['up']
            assert svstat('playground/tail') == ['up']

            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

            assert svstat('playground/date', 'playground/tail') == ['down', 'down']
        finally:
            check_call(('pgctl-2015', 'stop', 'date', 'tail'))

    def it_starts_everything_with_no_arguments_no_config(self, in_example_dir, request):
        try:
            check_call(('pgctl-2015', 'start'))

            assert svstat('playground/date') == ['up']
            assert svstat('playground/tail') == ['up']
        finally:
            check_call(('pgctl-2015', 'stop'))
