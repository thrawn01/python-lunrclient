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

from lunrclient.base import LunrHttpError, LunrError, response
from lunrclient.subcommand import SubCommand, SubCommandParser, opt, noargs
from lunrclient.client import LunrClient, StorageClient, Auth
from lunrclient.displayable import Displayable
from lunrclient.shared import Env, ShellError
import uuid
import os


class LunrCommand(SubCommand, Displayable):

    def __init__(self):
        # let the base class setup methods in our class
        SubCommand.__init__(self)
        # Add debug option to all commands (creates self.debug)
        self.opt('-d', '--debug', action='store_const',
                 const=True, default=False, help="print the REST calls used")

    def get_admin(self, required=True):
        result = self.admin or os.environ.get('LUNR_ADMIN')
        if required and not result:
            raise ShellError(self, "--admin or environ LUNR_ADMIN required")
        return result

    def filter(self, haystack, where):
        result = []
        for item in haystack:
            for key, value in where.items():
                if item[key] == value:
                    result.append(item)
        return response(result, haystack.get_code())

    def to_map(self, list, key):
        map = {}
        for item in list:
            map[item[key]] = item
        return map

    def translate(self, map, to):
        for key, value in to.iteritems():
            map[value] = map[key]
            del map[key]
        return map

    def required(self, require):
        results = {}
        for key in require:
            results[key] = os.environ.get(key)
            if results[key] is None or results[key] == '':
                raise LunrError("%s not set in enviroment, "
                                "and is required for Auth query" % key)
        return results

    def _is_connected(self, payload):
        if 'error' in payload:
            return '(error)'
        if payload:
            sessions = payload.get('sessions', [])
            ips = []
            for session in sessions:
                ips.append(session.get('ip', 'False'))
            if not ips:
                return 'False'
            return ','.join(ips)
        return '(not exported)'

    def _iqn(self, payload):
        if 'error' in payload:
            return '(error)'
        if payload:
            return payload.get('name', '(not exported)')
        return '(not exported)'

    def lunr_client_factory(self, tenant_id=None):
        tenant_id = tenant_id or os.environ.get('LUNR_TENANT_ID')
        # If DDI defined
        if tenant_id:
            return LunrClient(tenant_id, debug=self.debug)

        if self.debug:
            print("-- LUNR_TENANT_ID not set, attempting to contact"
                  " Auth to resolve tenant_id")

        # environment MUST have these defined if we want to
        # get the tenant_id from auth
        env = self.required(['LUNR_API_URL', 'OS_PASSWORD', 'OS_AUTH_URL',
                             'OS_USERNAME', 'OS_TENANT_NAME'])

        auth = Auth(auth_url=env['OS_AUTH_URL'],
                    tenant_name=env['OS_TENANT_NAME'],
                    user=env['OS_USERNAME'], password=env['OS_PASSWORD'])
        return LunrClient(auth.fetch_tenant_id(), debug=self.debug)


class Volume(LunrCommand):
    """
    Manage lunr volumes
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'volume'
        self.version = '1'
        # Setup any global options, then init SubCommand
        LunrCommand.__init__(self)
        self.opt('--tenant-id', default=None,
                 help="the tenant-id that owns the backup")
        self.opt('--admin', default=None, help="the admin tenant id")

    def pre_command(self):
        self.client = self.lunr_client_factory(self.tenant_id)

    @opt('-s', '--status', help="Filter the list by status")
    @opt('-a', '--account-id', help="Filter the list by account_id")
    @opt('-n', '--node-id', help="Filter the list by node_id")
    @opt('-i', '--id', help="Filter the list by volume id")
    @opt('-r', '--restore-of', help="Filter the list by restore_of")
    @opt('-N', '--no-nodes', action='store_true',
         help="show only the response, do not query for node details")
    def list(self, args):
        filters = self.remove(args, ['debug', 'tenant_id',
                                     'admin', 'no_nodes'])
        volumes = self.client.volumes.list(**filters)
        if args['no_nodes']:
            return self.display(volumes)

        headers = ['id', 'node-name', 'volume_type_name', 'restore_of',
                   'status', 'size']
        # Create a new client with ADMIN as the DDI to query the nodes
        client = LunrClient(self.get_admin(), debug=self.debug)
        nodes = self.to_map(client.nodes.list(), 'id')
        # Add the node name to the volume results
        for volume in volumes:
            volume['node-name'] = nodes[volume['node_id']]['name']

        self.display(volumes, headers)
        print("\nThis is a summary, use --no-nodes to see the entire response")

    @opt('-n', '--no-summary', action='store_true',
         help="show only the response")
    @opt('id', help="id that identifies the volume")
    def get(self, id, no_summary=False):
        # Get the Volume Information
        volume = self.client.volumes.get(id)
        if no_summary:
            return self.display(volume)

        # Get the Node Information
        client = LunrClient(self.get_admin(), debug=self.debug)
        node = client.nodes.get(volume['node_id'])
        volume['node-url'] = "http://%s:%s" % (node['hostname'], node['port'])
        try:
            # Get the export information from the storage node
            payload = StorageClient(volume['node-url'], debug=self.debug)\
                .exports.get(id)
        except LunrHttpError as e:
            payload = {}
            if e.code != 404:
                raise

        volume['node-url'] = "http://%s:%s" % (node['hostname'], node['port'])
        volume['in-use'] = self._is_connected(payload)
        volume['iqn'] = self._iqn(payload)
        self.display(volume, ['account_id', 'status', 'size', 'node_id',
                     'node-url', 'in-use', 'iqn', 'created_at',
                     'last_modified'])

        print("\nThis is a summary, use --no-summary "
              "to see the entire response")

    @opt('--id', help="id that will identify the new volume")
    @opt('--vtype', help="the type of volume to create")
    @opt('--diff-node', help="Create the volume on a different node than the"
         " node that contains the volume id specified; accepts multiple"
         "volume-id's separated by commas")
    @opt('--diff-group', help="Create the volume on a node that is in a"
         " different group than the group that contains the node with the"
         " volume id specified; accepts multiple volume-id's separated by"
         " commas")
    @opt('size', help="size of the new volume (in gigabytes)")
    def create(self, id=None, vtype=None, size=None,
               diff_node=None, diff_group=None):

        affinity=None
        if diff_node:
            affinity='different_node:%s' % diff_node
        if diff_group:
            affinity='different_group:%s' % diff_group

        vtype = vtype or 'vtype'
        result = self.client.volumes.create(id, vtype, size, affinity)
        self.display(result)

    @opt('--id', help="id that will identify the new volume")
    @opt('--volume-type-name', help="the type of volume to create")
    @opt('--size', help="size of the new volume (in gigabytes)", required=True)
    @opt('backup', help="backup id to restore from")
    def restore(self, args):
        kwargs = self.remove(args, ['name', 'debug', 'tenant_id', 'id'])
        result = self.client.volumes.restore(args['id'], **kwargs)
        self.display(result)

    @opt('id', help="id that identifies the volume")
    def delete(self, id=None):
        result = self.client.volumes.delete(id)
        self.display(result)

    @opt('id', help="id that identifies the volume")
    @opt('--status', required=True, help="Sets the status",
         choices=['ACTIVE', 'DELETED', 'DELETING', 'CLONING'])
    def update_status(self, id=None, status=None):
        volume = self.client.volumes.update_status(id, status)
        self.display(volume)


class Backup(LunrCommand):
    """
    Manage lunr backups
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'backup'
        # let the base class setup methods in our class
        LunrCommand.__init__(self)
        self.opt('--tenant-id', default=None,
                 help="the tenant-id that owns the backup")

    def pre_command(self):
        self.client = self.lunr_client_factory(self.tenant_id)

    @noargs
    def list(self):
        result = self.client.backups.list()
        self.display(result, ['id', 'volume_id', 'status',
                     'size', 'created_at'])

    @opt('id', help="id that identifies the backup")
    def get(self, id=None):
        result = self.client.backups.get(id)
        self.display(result)

    @opt('src', help="the volume id to create the backup from")
    @opt('--id', help="id that will identify the new backup")
    def create(self, id=None, src=None):
        result = self.client.backups.create(src, id)
        self.display(result)

    @opt('id', help="id that identifies the backup")
    def delete(self, id=None):
        result = self.client.backups.delete(id)
        self.display(result)


class Account(LunrCommand):
    """
    List lunr Accounts
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'account'
        # let the base class setup methods in our class
        LunrCommand.__init__(self)
        self.opt('--admin', default=None, help="the admin tenant-id")

    def pre_command(self):
        self.client = self.lunr_client_factory(self.get_admin())

    @opt('-a', '--all', action='store_true',
         help="display active and disabled nodes")
    def list(self, all=None):
        if all:
            resp = self.client.accounts.list()
        else:
            resp = self.client.accounts.list(status='ACTIVE')
        return self.display(resp, ['id', 'name', 'status'])

    @opt('-n', '--no-summary', action='store_true',
         help="show only the response")
    @opt('id', help="tenant-id to get")
    def get(self, id, no_summary=False):
        """ List details for a specific tenant id """
        resp = self.client.accounts.get(id)
        if no_summary:
            return self.display(resp)

        results = []
        # Get a list of all volumes for this tenant id
        client = LunrClient(self.get_admin(), debug=self.debug)
        volumes = client.volumes.list(account_id=resp['id'])
        #volumes = self.client.volumes.list(resp['id'])
        for volume in volumes:
            if volume['status'] == 'DELETED':
                continue
            results.append(volume)

        self.display(resp, ['name', 'status', 'last_modified', 'created_at'])
        if results:
            return self.display(response(results, 200),
                                ['id', 'status', 'size'])
        else:
            print("-- This account has no active volumes --")
        print("\nThis is a summary, use --no-summary "
              "to see the entire response")

    @opt('id', help="tenant id to create")
    def create(self, id):
        """ Create a new tenant id """
        resp = self.client.accounts.create(id=id)
        self.display(resp)

    @opt('id', help="tenant id to create")
    def delete(self, id):
        """ Delete an tenant id """
        resp = self.client.accounts.delete(id)
        self.display(resp)


class Node(LunrCommand):
    """
    Manage lunr nodes
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'node'
        # let the base class setup methods in our class
        LunrCommand.__init__(self)
        self.opt('--admin', default=None, help="the admin tenant id")

    def pre_command(self):
        self.client = self.lunr_client_factory(self.get_admin())

    @opt('-a', '--all', action='store_true',
         help="display active and disabled nodes")
    @opt('-s', '--dsh', action='store_true',
         help="Output a list of storage node hostnames for use with dsh")
    def list(self, all=None, dsh=None):
        resp = self.client.nodes.list()
        if not all:
            resp = self.filter(resp, where={'status': 'ACTIVE'})
        if dsh:
            for row in resp:
                print(row['name'])
        else:
            self.display(resp, ['id', 'name', 'status', 'volume_type_name',
                         'hostname', 'size'])

    def to_gb(self, volumes, field, dest=None):
        dest = dest or field
        for volume in volumes:
            volume[dest] = int(volume[field]) / (1024 ** 3)
        return volumes

    @opt('-n', '--no-summary', action='store_true',
         help="show only the response")
    @opt('id', help="id that identifies the node")
    def get(self, id=None, no_summary=False):
        node = self.client.nodes.get(id)
        if no_summary:
            return self.display(node)

        self.display(node)
        url = "http://%s:%s" % (node['hostname'], node['port'])
        volumes = StorageClient(url=url, debug=self.debug).volumes.list()
        self.to_gb(volumes, 'size', 'gigs')
        for i in range(0, len(volumes)):
            try:
                volumes[i]['tenant-id'] = self.client.volumes.get(
                    volumes[i]['id'])['account_id']
            except LunrHttpError as e:
                if e.code != 404:
                    raise
                volumes[i]['tenant-id'] = 'DELETING'

        print("")
        self.display(volumes, ['id', 'tenant-id', 'size', 'gigs'])

        print("\nThis is a summary, use --no-summary "
              "to see the entire response")

    @opt('-H', '--hostname', required=True, help='api hostname')
    @opt('-P', '--port', required=True, help="api port")
    @opt('-S', '--storage-hostname', required=True, help="storage hostname")
    @opt('-t', '--volume-type-name', required=True,
         help="type of storage (volume_type)")
    @opt('-s', '--size', required=True, help='size in GB')
    @opt('-n', '--name', help="name of the new node (defaults to uuid)")
    def create(self, args):
        try:
            name = args['name'] or str(uuid.uuid4())
            self.client.debug = args['debug']
            # Remove extra arguments
            args = self.remove(args, ['name', 'debug', 'admin'])
            result = self.client.nodes.create(name, **args)
            self.display(result)
        except LunrError as e:
            print("-- %s" % str(e))
            return 1

    @opt('-H', '--hostname', help='api hostname')
    @opt('-P', '--port', help="api port")
    @opt('-S', '--storage-hostname', help="storage hostname")
    @opt('-t', '--volume-type-name', help="type of storage (volume_type)")
    @opt('--status', help='Node Status (ACTIVE, PENDING)')
    @opt('-s', '--size', help='size in GB')
    @opt('name', help="name of the node to update")
    def update(self, args):
        try:
            name = args['name'] or str(uuid.uuid4())
            self.client.debug = args['debug']
            # Remove extra arguments
            args = self.remove(args, ['name', 'debug', 'admin'])
            result = self.client.nodes.update(name, **args)
            self.display(result)
        except LunrError as e:
            print("-- %s" % str(e))
            return 1

    @opt('id', help="id that identifies the node")
    def delete(self, id=None):
        result = self.client.nodes.delete(id)
        self.display(result)


class Export(LunrCommand):
    """
    Manage lunr Exports
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'export'
        # let the base class setup methods in our class
        LunrCommand.__init__(self)
        self.opt('--tenant-id', default=None,
                 help="the tenant id that owns the exports")

    def pre_command(self):
        self.client = self.lunr_client_factory()

    @opt('-I', '--initiator',
         help="the name of the initiator IE: iqn.2012-01-01.com.rackspace")
    @opt('-i', '--ip', help="the ip address the initiator will connect from")
    @opt('id', metavar='<VOLUME_ID>', help="id of the volume to export")
    def create(self, id, ip='0.0.0.0', initiator=''):
        resp = self.client.exports.create(id, ip, initiator)
        self.display(resp)

    @opt('id', help="the exported volume id to show")
    def get(self, id=None):
        resp = self.client.exports.get(id)
        self.display(resp)

    @opt('-f', '--force', action='store_true',
         help="detach even if initiator is still connected")
    @opt('id', help="the exported volume id to delete")
    def delete(self, id=None, force=False):
        resp = self.client.exports.delete(id, force=force)
        self.display(resp)

    @opt('-s', '--status', help="export status (ATTACHING, ??)")
    @opt('--instance-id', help="instance id")
    @opt('-I', '--initiator',
         help="the name of the initiator IE: iqn.2012-01-01.com.rackspace")
    @opt('-i', '--ip', help="the ip address the initiator will connect from")
    @opt('--mountpoint', help="mountpoint on the guest OS")
    @opt('--session-ip', help="")
    @opt('--session-initiator', help="")
    @opt('id', help="the exported volume id to update")
    def update(self, args):
        try:
            self.client.debug = args['debug']
            # Remove extra arguments
            kwargs = self.remove(args, ['id', 'debug', 'tenant_id'])
            self.display(self.client.exports.update(args['id'], **kwargs))
        except LunrError as e:
            print("-- %s" % str(e))
            return 1


def main():
    try:
        # Create the top-level parser
        desc = "Command line interface to the lunr api"
        parser = SubCommandParser([Backup(), Volume(), Env(),
                                  Node(), Export(), Account()],
                                  desc=desc)
        # execute the command requested
        return parser.run()

    except LunrHttpError as e:
        print("Code: %s - %s" % (e.code, e.msg))
        print(str(e))
    except LunrError as e:
        print(str(e))
    except ShellError as e:
        print(e.msg)
        return e.help()
    return 1
