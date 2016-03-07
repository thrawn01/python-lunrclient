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

from time import time
import requests
import json
import uuid


class LunrError(Exception):
    pass


class LunrHttpError(LunrError):

    def __init__(self, msg, code):
        self.msg = msg
        self.code = code

    def __str__(self):
        return self.msg


class ResponseList(list):
    def __init__(self, _list, code):
        self._code = code
        list.__init__(self, _list)

    def get_code(self):
        return self._code


class ResponseDict(dict):
    def __init__(self, _dict, code):
        self._code = code
        dict.__init__(self, _dict)

    def get_code(self):
        return self._code


def response(body, code):
    if isinstance(body, list):
        return ResponseList(body, code)
    return ResponseDict(body, code)


class BaseAPI(object):

    def __init__(self, client):
        self.debug = client.debug
        self.client = client
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "python-lunrclient"
        }
        if client.headers:
            self.headers.update(client.headers)
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def buildUrl(self, uri):
        return "%s%s" % (self.client.url, uri)

    def http_request(self, call, url, **kwargs):
        try:
            # Remove args with no value
            kwargs = self.unused(kwargs)
            if self.client.timeout:
                kwargs['timeout'] = self.client.timeout

            if self.debug:
                print("-- %s on %s with %s " % (call.__name__.upper(),
                                                url, kwargs))
            resp = call(url, **kwargs)
            if self.debug:
                print("-- response: %s " % resp.text)
            if resp.status_code != 200:
                raise LunrHttpError("%s returned '%s' with '%s'" %
                                    (url, resp.status_code,
                                     json.loads(resp.text)['reason']),
                                    resp.status_code)
            return response(json.loads(resp.text), resp.status_code)
        except requests.RequestException as e:
            raise LunrError(str(e))

    def http_get(self, uri, **kwargs):
        return self.http_request(self.session.get,
                                 self.buildUrl(uri), **kwargs)

    def http_put(self, uri, **kwargs):
        return self.http_request(self.session.put,
                                 self.buildUrl(uri), **kwargs)

    def http_delete(self, uri, **kwargs):
        return self.http_request(self.session.delete,
                                 self.buildUrl(uri), **kwargs)

    def http_post(self, uri, **kwargs):
        return self.http_request(self.session.post,
                                 self.buildUrl(uri), **kwargs)

    def unused(self, _dict):
        """
        Remove empty parameters from the dict
        """
        for key, value in _dict.items():
            if value is None:
                del _dict[key]
        return _dict

    def required(self, method, _dict, require):
        """
        Ensure the required items are in the dictionary
        """
        for key in require:
            if key not in _dict:
                raise LunrError("'%s' is required argument for method '%s'"
                                % (key, method))

    def allowed(self, method, _dict, allow):
        """
        Only these items are allowed in the dictionary
        """
        for key in _dict.keys():
            if key not in allow:
                raise LunrError("'%s' is not an argument for method '%s'"
                                % (key, method))


class StorageAPI(BaseAPI):

    def __init__(self, client):
        BaseAPI.__init__(self, client)
        self.version = 'v1.0'

    def buildUrl(self, uri):
        return "%s%s" % (self.client.url, uri)


class StorageStatus(StorageAPI):

    def list(self):
        """
        Return stats on the api status
        """
        return self.http_get('/status')

    def api(self):
        """
        Return stats on the api status
        """
        return self.http_get('/status/api')

    def conf(self):
        """
        Return the storage node configuration
        """
        return self.http_get('/status/conf')


class StorageVolume(StorageAPI):

    def list(self):
        """
        list all available volumes on the storage node
        """
        return self.http_get('/volumes')

    def get(self, volume_id):
        """
        get the details of a volume
        """
        return self.http_get('/volumes/%s' % volume_id)

    def create(self, size, volume_id=None):
        """
        create a volume of the specified size
        """
        volume_id = volume_id or str(uuid.uuid4())
        return self.http_put('/volumes/%s' % volume_id,
                             params=self.unused({'size': size}))

    def clone(self, source_id, backup_id, size,
              volume_id=None, source_host=None):
        """
        create a volume then clone the contents of
        the backup into the new volume
        """
        volume_id = volume_id or str(uuid.uuid4())
        return self.http_put('/volumes/%s' % volume_id,
                             params=self.unused({
                                 'source_host': source_host,
                                 'source_volume_id': source_id,
                                 'backup_id': backup_id,
                                 'size': size
                             }))

    def delete(self, volume_id):
        """
        delete a volume
        """
        return self.http_delete('/volumes/%s' % volume_id)

    def audit(self, volume_id):
        """
        Run an audit job that compares the backup manifest with the blocks
        stored in swift, deleting any blocks that are no longer in the manifest
        """
        return self.http_put('/volumes/%s/audit' % volume_id)

    def lock(self, volume_id):
        """
        Get lock file info for a volume
        """
        return self.http_get('/volumes/%s/lock' % volume_id)


class StorageBackup(StorageAPI):

    def list(self, volume_id):
        """
        list all the available backups for this volume
        """
        return self.http_get('/volumes/%s/backups' % volume_id)

    def get(self, volume_id, backup_id):
        """
        get the details of a backup
        """
        return self.http_get('/volumes/%s/backups/%s' % (volume_id, backup_id))

    def create(self, volume_id, backup_id=None, timestamp=None):
        """
        create a backup of a volume
        """
        backup_id = backup_id or str(uuid.uuid4())
        timestamp = timestamp or int(time())
        return self.http_put('/volumes/%s/backups/%s' % (volume_id, backup_id),
                             params={'timestamp': timestamp})

    def delete(self, volume_id, backup_id):
        """
        delete the specified backup
        """
        return self.http_delete('/volumes/%s/backups/%s' %
                                (volume_id, backup_id))


class StorageExport(StorageAPI):

    def get(self, volume_id):
        """
        get the details of an export
        """
        return self.http_get('/volumes/%s/export' % volume_id)

    def create(self, volume_id, ip=None):
        """
        create an export for a volume
        """
        if ip:
            return self.http_put('/volumes/%s/export?ip=%s' % (volume_id, ip))
        return self.http_put('/volumes/%s/export' % volume_id)

    def delete(self, volume_id, force=False):
        """
        delete an export
        """
        return self.http_delete('/volumes/%s/export' % volume_id,
                                params={'force': force})


class LunrAPI(BaseAPI):

    def __init__(self, client):
        BaseAPI.__init__(self, client)
        self.client = client
        self.version = 'v1.0'

    def buildUrl(self, uri):
        return "%s/%s/%s%s" % (self.client.url, self.version,
                               self.client.tenant_id, uri)


class LunrVolume(LunrAPI):

    def list(self, **kwargs):
        """
        list all the available volumes for this tenant_id
        You can filter the results returned by the api with
        these parameters ['status', 'account_id', 'node_id', 'id']
        """
        return self.http_get('/volumes', params=kwargs)

    def get(self, volume_id):
        """
        get the details of a volume
        """
        return self.http_get('/volumes/%s' % (volume_id))

    def create(self, volume_id, vtype, size, affinity):
        """
        create a volume
        """
        volume_id = volume_id or str(uuid.uuid4())
        params = { 'volume_type_name': vtype,
                   'size': size,
                   'affinity': affinity
        }
        return self.http_put('/volumes/%s' % volume_id,
                             params=self.unused(params))

    def restore(self, volume_id, **kwargs):
        """
        restore a volume from a backup
        """
        # These arguments are required
        self.required('create', kwargs, ['backup', 'size'])
        # Optional Arguments
        volume_id = volume_id or str(uuid.uuid4())
        kwargs['volume_type_name'] = kwargs['volume_type_name'] or 'vtype'
        kwargs['size'] = kwargs['size'] or 1
        # Make the request
        return self.http_put('/volumes/%s' % volume_id,
                             params=self.unused(kwargs))

    def delete(self, volume_id):
        """
        delete a volume
        """
        return self.http_delete('/volumes/%s' % volume_id)

    def update_status(self, volume_id, status):
        """
        Update the status of a volume
        """
        return self.http_post('/volumes/%s' % volume_id,
                              params={'status': status})


class LunrBackup(LunrAPI):

    def list(self, **kwargs):
        """
        list all the available backups for this account

        filters: status, account_id, id, volume_id
        """
        return self.http_get('/backups', params=kwargs)

    def get(self, backup_id):
        """
        get the details of a backup
        """
        return self.http_get('/backups/%s' % backup_id)

    def create(self, volume_id, backup_id):
        """
        create a backup
        """
        backup_id = backup_id or str(uuid.uuid4())
        return self.http_put('/backups/%s' % backup_id,
                             params={'volume': volume_id})

    def update(self, backup_id, params=None):
        """
        update the information on the backup
        (This does not re-create the backup on the storage node)
        """
        return self.http_post('/backups/%s' % backup_id, params=params)

    def delete(self, backup_id):
        """
        delete a backup
        """
        return self.http_delete('/backups/%s' % backup_id)


class LunrAccount(LunrAPI):

    def list(self, **kwargs):
        """
        list all the available accounts

        filters: status, id
        """
        return self.http_get('/accounts', params=kwargs)

    def get(self, account_id):
        """
        get the details of an account
        """
        return self.http_get('/accounts/%s' % account_id)

    def create(self, **kwargs):
        """
        create a new account
        """
        self.required('create', kwargs, ['id'])
        return self.http_post('/accounts', params=kwargs)

    def delete(self, account_id):
        """
        delete an account
        """
        return self.http_delete('/accounts/%s' % account_id)


class LunrNode(LunrAPI):

    def list(self, **kwargs):
        """
        list all the available nodes

        filters: name, status, volume_type_name
        """
        return self.http_get('/nodes', params=kwargs)

    def get(self, node_id):
        """
        get the details of a node
        """
        return self.http_get('/nodes/%s' % node_id)

    def create(self, name, **kwargs):
        """
        Create a new node
        """
        # These arguments are required
        self.required('create', kwargs, ['hostname', 'port',
                      'storage_hostname', 'volume_type_name', 'size'])
        kwargs['name'] = name
        return self.http_post('/nodes', params=kwargs)

    def update(self, name, **kwargs):
        """
        Create a new node
        """
        # These arguments are allowed
        self.allowed('update', kwargs, ['hostname', 'port', 'status',
                     'storage_hostname', 'volume_type_name', 'size'])
        # Remove parameters that are None
        kwargs = self.unused(kwargs)
        return self.http_post('/nodes/%s' % name, params=kwargs)

    def delete(self, node_id):
        """
        delete a node
        """
        return self.http_delete('/nodes/%s' % node_id)


class LunrExport(LunrAPI):

    def get(self, volume_id):
        """
        get the details of an export
        """
        return self.http_get('/volumes/%s/export' % volume_id)

    def create(self, volume_id, ip, initiator):
        """
        create an export for a volume
        """
        return self.http_put('/volumes/%s/export' % volume_id, params={
                             'ip': ip,
                             'initiator': initiator
                             })

    def delete(self, volume_id, force=False):
        """
        delete an export
        """
        return self.http_delete('/volumes/%s/export'
                                % volume_id, params={'force': force})

    def update(self, volume_id, **kwargs):
        """
        update an export
        """
        # These arguments are allowed
        self.allowed('update', kwargs, ['status', 'instance_id',
                     'mountpoint', 'ip', 'initiator', 'session_ip',
                     'session_initiator'])
        # Remove parameters that are None
        params = self.unused(kwargs)
        return self.http_post('/volumes/%s/export' % volume_id, params=params)
