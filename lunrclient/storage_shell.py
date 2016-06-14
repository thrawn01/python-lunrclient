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

from lunrclient.subcommand import SubCommand, SubCommandParser, opt, noargs
from lunrclient.client import StorageClient
from lunrclient.displayable import Displayable
from lunrclient.shared import Env, ShellError
from lunrclient.base import LunrError, LunrHttpError
from pprint import pprint

try:
    from lunrclient.tools import Tools
except ImportError:
    print("-- Warning: Failed to load tools module, Missing dependency?")
    Tools = object


class StorageCommand(SubCommand, Displayable):

    def __init__(self):
        # let the base class setup methods in our class
        SubCommand.__init__(self)
        # Add debug option to all commands (creates self.debug)
        self.opt('-d', '--debug', action='store_const',
                 const=True, default=False, help="print the REST calls used")
        self.opt('-H', '--host', default=None,
                 help="hostname or ip for the storage node")

    def pre_command(self):
        if self.host:
            self.storage = StorageClient(url="http://%s:8081" % self.host,
                                         debug=self.debug)
        else:
            self.storage = StorageClient(debug=self.debug)


class Volume(StorageCommand):
    """
    Direct inteface with the lunr storage volume api
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'volume'
        # let the base class setup methods in our class
        StorageCommand.__init__(self)

    @noargs
    def list(self):
        result = self.storage.volumes.list()
        self.display(result, ['id', 'path', 'size'])

    @opt('id', help="volume id to get")
    def get(self, id=None):
        result = self.storage.volumes.get(id)
        self.display(result)

    @opt('--id', help="volume id to identify the volume")
    @opt('size', help="size of the new volume (in gigabytes)")
    def create(self, id=None, size=0):
        result = self.storage.volumes.create(size, volume_id=id)
        self.display(result)

    @opt('--id', help="volume id to identify the new volume")
    @opt('--src', help="volume id to clone from")
    @opt('--backup', help="backup id to retrieve from")
    @opt('size', help='size of the new volume (must be the"\
            " same or larger than the original backup)')
    def clone(self, id=None, src=None, backup=None, size=None, src_host=None):
        if not (src or backup):
            raise ShellError(self, "options --src or --backup are required")
        if not size:
            raise ShellError(self, "size is required")
        if not src:
            if not src_host:
                raise ShellError(self, "--src-host is required "
                                       "when using --src")
        result = self.storage.volumes.clone(src, backup, size,
                                            src_host, volume_id=id)
        self.display(result)

    @opt('id', help="volume id to delete")
    def delete(self, id=None):
        result = self.storage.volumes.delete(id)
        self.display(result)

    @opt('id', help="volume id to audit")
    def audit(self, id=None):
        result = self.storage.volumes.audit(id)
        self.display(result)

    @opt('id', help="volume id to get lock info from")
    def lock(self, id=None):
        result = self.storage.volumes.lock(id)
        self.display(result)


class Backup(StorageCommand):
    """
    Direct inteface with the lunr storage backup api
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'backup'
        # let the base class setup methods in our class
        StorageCommand.__init__(self)

    @opt('src', metavar='<src-volume-id>', help="list all backups for "
         "specified volume id")
    def list(self, src):
        result = self.storage.backups.list(src)
        pprint(result)

    @opt('id', metavar='<backup-id>', help="backup id to get")
    @opt('src', metavar='<src-volume-id>', help="volume id the backup is from")
    def get(self, src=None, id=None):
        result = self.storage.backups.get(src, id)
        self.display(result)

    @opt('src', metavar='<src-volume-id>',
         help="volume id to create the backup from")
    @opt('--id', help="backup id to identify the backup")
    @opt('--timestamp', help="timestamp used to mark the time of the backup")
    def create(self, src, id=None, timestamp=None):
        result = self.storage.backups.create(src, backup_id=id,
                                             timestamp=timestamp)
        self.display(result)

    @opt('id', metavar='<backup-id>', help="backup id to delete")
    @opt('src', metavar='<src-volume-id>',
         help="volume id the backup was created from")
    def delete(self, src, id):
        result = self.storage.backups.delete(src, id)
        self.display(result)


class Status(StorageCommand):
    """
    Access to the status api on a storage node
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'status'
        # let the base class setup methods in our class
        StorageCommand.__init__(self)

    @noargs
    def list(self):
        self.display(self.storage.status.list())

    @noargs
    def api(self):
        self.display(self.storage.status.api())

    @noargs
    def conf(self):
        self.display(self.storage.status.conf())


class Export(StorageCommand):
    """
    Direct inteface with the lunr storage backup api
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'export'
        # let the base class setup methods in our class
        StorageCommand.__init__(self)

    @opt('id', help="the exported volume id to show")
    def get(self, id):
        self.display(self.storage.exports.get(id))

    @opt('-i', '--ip', help="the ip address that will connect to the export")
    @opt('id', help="the volume id to export")
    def create(self, id, ip=None):
        self.display(self.storage.exports.create(id, ip))

    @opt('-f', '--force', action='store_true',
         help="detach even if initiator is still connected")
    @opt('id', help="the exported volume id to delete")
    def delete(self, id, force=False):
        self.display(self.storage.exports.delete(id, force=force))


def main():
    try:
        # Create the top-level parser
        desc = "Command line interface to the lunr storage api"
        parser = SubCommandParser([Backup(), Volume(), Env(),
                                   Tools(), Status(), Export()], desc=desc)
        # execute the command requested
        return parser.run()

    except LunrHttpError as e:
        print("Code: %s - %s" % (e.code, e.msg))
    except LunrError as e:
        print(str(e))
    except ShellError as e:
        print(e.msg)
        return e.help()
