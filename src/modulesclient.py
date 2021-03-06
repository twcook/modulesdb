# -*- coding: utf-8 -*-

# Copyright 2013 Justin Makeig <<https://github.com/jmakeig>>
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

import urllib
import requests
from requests.auth import HTTPDigestAuth
from requests.auth import HTTPBasicAuth

class ModulesClient(object):

    def __init__(self, config):
        # print config
        self.url = config.get('url')
        self.auth_type = config.get('auth')
        self.user = config.get('user')
        self.password = config.get('password')
        self.database = config.get('database')
        cert = None
        cert_password = None
        self.root = config.get('root')
        # config.get('permissions') should be a list of {"role": "privilege"} pairs.
        self.permissions = config.get('permissions')

        if self.auth_type == "none":
            self.auth = None
        elif self.auth_type == "digest":
            self.auth = HTTPDigestAuth(self.user, self.password)
        elif self.auth_type == "basic":
            self.auth = HTTPBasicAuth(self.user, self.password)
        else: 
            raise Exception("Unsupported auth_type " + self.auth_type)

        self._config()

    def _config(self):
        "Set the default error format as JSON for easier conversion into Python data structures."
        # http://localhost:8003/v1/config/properties/error-format?format=json
        # {"error-format": "json"}
        # r = requests.put(
        #     self.url + "/v1/config/properties/error-format", 
        #     params={"format": "json"}, 
        #     headers={}, 
        #     auth=self.auth,
        #     data='{"error-format": "json"}'
        # )
        # if r.status_code > 299 or r.status_code < 200:
        #     raise Exception(r.status_code, r.text)

    def put(self, uri, body, transaction=None):
        "Send a file to the remote modules database. URIs are prepended with the root."
        params = {"uri": self.root + uri}
        params.update(self.permissions)
        if transaction is not None:
            params['txid'] = transaction
        if self.database is not None:
            params['database'] = self.database
        headers = {}
        r = requests.put(
            self.url + "/v1/documents", 
            params=params, 
            headers=headers, 
            auth=self.auth,
            data=body
        )
        if r.status_code > 299 or r.status_code < 200:
            raise Exception(r.status_code, r.text)
        return ("PUT", r.status_code, params['uri'])

    def put_file(self, uri, file_path, transaction=None):
        "Open a file for reading, put its contents using self.put, and close it."
        f = open(file_path, "r")
        msg = self.put(uri=uri, body=f.read(), transaction=transaction)
        f.close()
        return msg

    def delete(self, uri, transaction=None):
        "Delete a remote file identified by the URI."
        params = {"uri": self.root + uri}
        if transaction is not None:
            params['txid'] = transaction
        if self.database is not None:
            params['database'] = self.database
        headers = {}
        r = requests.delete(
            self.url + "/v1/documents", 
            params=params, 
            headers=headers, 
            auth=self.auth
        )
        if r.status_code > 299 or r.status_code < 200:
            raise Exception(r.status_code)
        return ("DELETE", r.status_code, self.root + uri)

    def move(self, from_uri, to_uri, body, transaction=None):
        pass

    def move_file(self, from_uri, to_uri, file_path, transaction=None):
        tx = transaction
        if transaction is None:
            tx = self._create_transaction();
        self.delete(from_uri, tx)
        msg = self.put_file(to_uri, file_path, tx)
        self._commit_transaction(tx)
        return ("MOVE", msg[1], self.root + to_uri)

    def _create_transaction(self):
        "Create a transaction and return its id"
        params = {}
        if self.database is not None:
            params['database'] = self.database
        r = requests.post(
            self.url + "/v1/transactions",
            auth=self.auth,
            allow_redirects=False,
            params=params
        )
        if r.status_code != 303:
            raise Exception(r.status_code)
        return r.headers['Location'].split('/')[3]

    def _commit_transaction(self, transaction):
        "Commit a transaction"
        params = {"result": "commit"}
        if self.database is not None:
            params['database'] = self.database
        r =  requests.post(
            self.url + "/v1/transactions/" + transaction,
            params=params,
            auth=self.auth
        )
        if r.status_code > 299 or r.status_code < 200:
            raise Exception(r.status_code)
