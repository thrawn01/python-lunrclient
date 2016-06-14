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

import requests
import json


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
