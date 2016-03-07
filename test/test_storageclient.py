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

from unittest import TestCase
from lunrclient.client import StorageClient

from requests_mock import Adapter
from json import dumps


class TestStorageClient(TestCase):

    def test_list(self):
        client = StorageClient("mock://")
        adapter = Adapter()

        # should probably figure out a better way to do this
        client.volumes.session.mount('mock', adapter)

        adapter.register_uri('GET', 'mock:///volumes', text=dumps([{
                "export": {},
                "id": "thrawn",
                "name": "thrawn",
                "origin": "",
                "path": "/dev/lunr-volume/thrawn",
                "size": 12582912
            }])
        )

        # List all the volumes on a storage node
        volumes = client.volumes.list()

        # Asserts
        self.assertIn('export', volumes[0])
        self.assertIn('id', volumes[0])
        self.assertIn('origin', volumes[0])
        self.assertIn('path', volumes[0])
        self.assertIn('size', volumes[0])
