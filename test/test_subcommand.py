# Copyright 2011-2016 Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from lunrclient.subcommand import SubCommand, SubCommandParser, opt, noargs
from argparse import ArgumentParser
from unittest import TestCase


class Api(SubCommand):
    """
    Provides a command line interface to the API
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'api'
        # let the base class setup methods in our class
        SubCommand.__init__(self)

    @opt('--name', help='Name of the thingy')
    def create(self, name=None):
        """
        Create a new volume
        """
        return "create: %s" % name

    @noargs
    def list(self):
        """
        List all available volumes
        """
        return "listing"

    def help(self):
        return "help"


class TestSubCommands(TestCase):

    def setUp(self):
        self.parser = SubCommandParser([Api()])

    def test_opt_decorator(self):
        # run the 'create' method on sub command 'api'
        result = self.parser.run('api create --name derrick'.split())
        self.assertEqual(result, "create: derrick")

    def test_noargs(self):
        result = self.parser.run('api list'.split())
        self.assertEqual(result, "listing")

    def test_no_subcommand(self):
        result = self.parser.run('api'.split())
        self.assertEqual(result, "help")

