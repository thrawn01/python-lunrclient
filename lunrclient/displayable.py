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

from prettytable import PrettyTable


class Displayable(object):

    def display(self, results, headers=None):
        self._display(results, headers)
        # If the response is not 200, show the user
        if results.get_code() != 200:
            print("\n-- HTTP Code: %s --" % results.get_code())

    def _display(self, results, headers=None):
        # No results?
        if len(results) == 0:
            print("-- Empty Response --")
            return

        # JSON might return a single response
        if not isinstance(results, list):
            # Only include items in 'headers'
            results = self._filter(results, headers)
            # Display the single item and return
            print(self.format(results, 0))
            return

        # Assume this is a list of items and build a table
        # Get the headers from the first row in the result
        if not headers:
            headers = results[0].keys()

        table = PrettyTable(headers)

        # Iterate through the rows
        for row in results:
            # Extract the correct columns for each row
            table.add_row(self._build_row(row, headers))

        # Print the table
        print(table)

    def _build_row(self, row, headers):
        result = []
        for key in headers:
            if key in row:
                result.append(row[key])
            else:
                result.append('')
        return result

    def _filter(self, dict, keep):
        """ Remove any keys not in 'keep' """
        if not keep:
            return dict

        result = {}
        for key, value in dict.iteritems():
            if key in keep:
                result[key] = value
        return result

    def _longest_len(self, items):
        longest = 0
        for item in items:
            if len(item) > longest:
                longest = len(item)
        return longest

    def _item(self, value, offset):
        return "%s%s" % (' ' * offset, self._format(value, offset))

    def _pair(self, key, value, offset):
        return ('%' + str(offset) + 's: %s') % (key, self._format(value,
                                                                  offset))

    def format(self, *args, **kwargs):
        return self._format(*args, **kwargs)[2:-4]

    def _format(self, value, offset=0):
        if isinstance(value, list):
            result = [self._item(it, offset + 5)
                      for it in value]
            if len(result):
                return "[\n%s\n%s]" % (',\n'.join(result), ' ' * (offset + 2))
            return "[]"
        if isinstance(value, dict):
            align = self._longest_len(value)
            result = [self._pair(key, _value, (offset + 4) + align)
                      for key, _value in value.iteritems()]
            if len(result):
                return "{\n%s\n%s}" % ('\n'.join(result), ' ' * (offset + 2))
            return "{}"
        return "%s" % value
