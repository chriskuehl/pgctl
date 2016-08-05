# -*- coding: utf-8 -*-
# pylint:disable=no-self-use
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import six
from frozendict import frozendict
from testfixtures import ShouldRaise
from testing.norm import norm_trailing_whitespace_json

from pgctl.errors import LockHeld
from pgctl.functions import bestrelpath
from pgctl.functions import JSONEncoder
from pgctl.functions import show_runaway_processes


class DescribeJSONEncoder(object):

    def it_encodes_frozendict(self):
        test_dict = frozendict({
            'pgdir': 'playground',
            'services': ('default',),
            'aliases': frozendict({
                'default': ('')
            }),
        })
        result = JSONEncoder(sort_keys=True, indent=4).encode(test_dict)
        assert norm_trailing_whitespace_json(result) == '''\
{
    "aliases": {
        "default": ""
    },
    "pgdir": "playground",
    "services": [
        "default"
    ]
}'''

    def it_encodes_other(self):
        msg = 'type' if six.PY2 else 'class'
        with ShouldRaise(TypeError("<{} 'object'> is not JSON serializable".format(msg))):
            JSONEncoder(sort_keys=True, indent=4).encode(object)


class DescribeBestrelpath(object):

    def it_prefers_shorter_strings(self):
        assert bestrelpath('/a/b/c', '/a/b') == 'c'
        assert bestrelpath('/a/b', '/a/b/c') == '/a/b'
        assert bestrelpath('/a/b', '/a/b/c/d') == '/a/b'


class DescribeShowRunawayProcesses(object):

    def it_fails_when_there_are_locks(self, tmpdir):
        lockfile = tmpdir.ensure('lock')
        lock = lockfile.open()

        with ShouldRaise(LockHeld):
            show_runaway_processes(lockfile.strpath)

        lock.close()

        show_runaway_processes(lockfile.strpath)

    def it_passes_when_there_are_no_locks(self, tmpdir):
        assert show_runaway_processes(tmpdir.strpath) is None
