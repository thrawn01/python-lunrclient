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

from __future__ import print_function

from lunrclient.subcommand import SubCommand
import os


class ShellError(Exception):

    # TODO: Getting the correct help message needs work
    def __init__(self, instance, msg):
        self.help = instance.help
        self.msg = msg

    def __str__(self):
        return self.msg


class Env(SubCommand):
    """
    Display Available environment options
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'env'
        # let the base class setup methods in our class
        SubCommand.__init__(self)

    def help(self):
        print("# Available environment variables")
        print("export OS_TENANT_NAME='%s'" % os.environ['USER'])
        print("export LUNR_ADMIN='admin'")
        print("export LUNR_TENANT_ID='admin'")
        print("export LUNR_STORAGE_URL='http://localhost:8081'")
        print("export LUNR_API_URL='http://localhost:8080'")
        print("")
        print("# Used by Auth to fetch a TENANT_NAME's DDI")
        print("export OS_USERNAME='demo'")
        print("export OS_PASSWORD='devstack'")
        print("export OS_AUTH_URL='http://localhost:5000/v2.0'")
        return 0
