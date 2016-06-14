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

import os
import json

from lunrclient.lunr import LunrVolume, LunrBackup, LunrAccount, LunrNode, LunrExport
from lunrclient.storage import StorageVolume, StorageStatus, StorageExport, StorageBackup
from lunrclient.base import BaseAPI, LunrError


class LunrClient(object):

    def __init__(self, tenant_id, debug=False, timeout=None,
                 http_agent=None, url=None, headers=None):
        self.headers = headers
        if http_agent:
            if not self.headers:
                self.headers = {}
            self.headers['User-Agent'] = http_agent
        self.debug = debug
        self.version = '1'
        self.tenant_id = tenant_id
        self.url = url
        self.timeout = timeout

        if self.tenant_id is None:
            raise LunrError("LunrClient() requires valid tenant_id")
        if self.url is None:
            self.url = os.environ.get('LUNR_API_URL', 'http://localhost:8080')

        self.volumes = LunrVolume(self)
        self.backups = LunrBackup(self)
        self.accounts = LunrAccount(self)
        self.nodes = LunrNode(self)
        self.exports = LunrExport(self)

    def as_tenant_id(self, tenant_id):
        self.tenant_id = tenant_id


class StorageClient(object):

    def __init__(self, url=None, debug=False, headers=None, timeout=None):
        self.timeout = timeout
        self.headers = headers
        self.debug = debug
        self.version = '1'
        self.url = url
        if self.url is None:
            self.url = os.environ.get('LUNR_STORAGE_URL',
                                      'http://localhost:8081')

        self.volumes = StorageVolume(self)
        self.status = StorageStatus(self)
        self.exports = StorageExport(self)
        self.backups = StorageBackup(self)


class Auth(BaseAPI):

    def __init__(self, auth_url, tenant_name, user, password,
                 debug=False, headers=None, timeout=None):
        self.tenant_name = tenant_name
        self.password = password
        self.auth_url = auth_url
        self.headers = headers
        self.timeout = timeout
        self.debug = debug
        self.user = user
        BaseAPI.__init__(self, self)

    def fetch_tenant_id(self):
        payload = {
            "auth": {
                "tenantName": self.tenant_name,
                "passwordCredentials": {
                    "username": self.user,
                    "password": self.password
                }
            }
        }
        # Can't use http_post because we are encoding json in the body
        resp = self.http_request(self.session.post,
                                 "%s/tokens" % self.auth_url,
                                 data=json.dumps(payload))
        if self.debug:
            print("-- DDI: ", resp['access']['token']['tenant']['id'])
        return resp['access']['token']['tenant']['id']
