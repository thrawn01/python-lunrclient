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

from lunr.storage.helper.volume import VolumeHelper, encode_tag
from lunrclient.subcommand import SubCommand, opt
from lunr.storage.helper.utils.worker import BLOCK_SIZE
from lunr.storage.helper.backup import BackupHelper
from lunr.storage.helper.utils import directio
from lunr.storage.helper.utils import execute
from lunr.common.config import LunrConfig
from contextlib import contextmanager
from time import time
from lunr.common import logger
from os.path import exists
from pprint import pprint
from six.moves import range
import logging
import random
import sys
import os
import re

from collections import defaultdict


class Tools(SubCommand):
    """
    A collection of misc Storage Node tools
    """

    def __init__(self):
        # Give our sub command a name
        self._name = 'tools'
        # Create a volume helper with our local storage config
        self.volume = VolumeHelper(LunrConfig.from_storage_conf())
        # let the base class setup methods in our class
        SubCommand.__init__(self)
        self.total = defaultdict(float)

    def dot(self):
        sys.stdout.write('.')
        sys.stdout.flush()

    def get_volume(self, id):
        """
        return volume information if the argument is an id or a path
        """
        # If the id is actually a path
        if exists(id):
            with open(id) as file:
                size = os.lseek(file.fileno(), 0, os.SEEK_END)
            return {'path': id, 'size': size}
        return self.volume.get(id)

    def _remove_volume(self, path):
        try:
            self.volume.remove(path)
        except Exception as e:
            print("Remove Failed: %s" % e)

    @opt('device',
         help="volume id or /path/to/block-device to randomize writes to")
    @opt('--precent', help="precent of the volume should we randomize")
    @opt('--silent', help="run silent", action='store_const', const=True)
    def randomize(self, device=None, percent=100, silent=False):
        """
        Writes random data to the beginning of each 4MB block on a block device
        this is useful when performance testing the backup process

        (Without any optional arguments will randomize the first 32k of each
        4MB block on 100 percent of the device)
        """
        volume = self.get_volume(device)
        # The number of blocks in the volume
        blocks = int(volume['size'] / BLOCK_SIZE)
        # How many writes should be to the device
        # (based on the percentage requested)
        num_writes = int(blocks * percent * 0.01)
        # Build a list of offsets we write to
        offsets = sorted(random.sample(range(blocks), num_writes))
        total = 0

        if not silent:
            print('Writing urandom to %s bytes in %s' % (volume['size'],
                                                         volume['path']))

        with open(volume['path'], 'w') as file:
            for offset in offsets:
                if not silent:
                    self.dot()
                file.seek(offset * BLOCK_SIZE)
                # Create a random string 32k long then duplicate
                # the randomized string 128 times (32768 * 128 = 4MB)
                data = os.urandom(32768) * 128
                total += len(data)
                # write out the 4MB block of randomized data
                file.write(data)
        print("\nWrote: %s" % total)

    @opt('device', help="volume id or /path/to/block-device to read")
    @opt('--offset', help="the offset in blocks to start the read")
    @opt('--count', help="the number of blocks to read")
    @opt('--bs', help="size of the block to read (default: %s)" % BLOCK_SIZE)
    def read(self, device=None, offset=0, bs=None, count=1):
        """
        Using DIRECT_O read from the block device specified to stdout
        (Without any optional arguments will read the first 4k from the device)
        """
        volume = self.get_volume(device)
        block_size = bs or BLOCK_SIZE

        offset = int(offset) * block_size
        count = int(count)
        print("Offset: ", offset)

        total = 0
        with directio.open(volume['path'], buffered=block_size) as file:
            file.seek(offset)
            for i in range(0, count):
                total += os.write(sys.stdout.fileno(), file.read(block_size))
        os.write(sys.stdout.fileno(), "\nRead: %d Bytes\n" % total)

    @opt('device', help="volume id or /path/to/block-device to read")
    @opt('--char',
         help="the character to write to the block device (default: 0)")
    @opt('--count',
         help="the number of blocks to write (default: size of device)")
    @opt('--bs', help="size of the block to write (default: %s)" % BLOCK_SIZE)
    def write(self, device=None, char=0, bs=None, count=None):
        """
        Using DIRECT_O write a character in 4k chunks to a specified block
        device (Without any optional arguments will write NULL's to the
        entire device)
        """
        volume = self.get_volume(device)
        block_size = bs or BLOCK_SIZE

        # Calculate the number of blocks that are in the volume
        count = count or (volume['size'] / block_size)

        data = "".join([chr(int(char)) for i in range(0, block_size)])

        print("Writing: '%c'" % data[0])
        total = 0
        with directio.open(volume['path'], buffered=block_size) as file:
            for i in range(0, count):
                self.dot()
                total += file.write(data)
        print("\nWrote: ", total)
        return 0

    @contextmanager
    def timeit(self, size):
        before = time()
        yield
        secs = time() - before
        print("Elapsed: %s" % secs)
        print("Throughput: %0.2f MB/s" % ((int(size) / secs) / 1048576))

    @opt('id', help="backup id to identify the backup")
    @opt('--src', help="volume id to create the backup from", required=True)
    @opt('--timestamp', help="the timestamp used on the backup")
    def backup(self, id=None, src=None, timestamp=None):
        """
        This runs a backup job outside of the storage api,
        which is useful for performance testing backups
        """
        # Set basic Logging
        logging.basicConfig()
        # Get the lunr logger
        log = logger.get_logger()
        # Output Debug level info
        log.logger.setLevel(logging.DEBUG)
        # Load the local storage configuration
        conf = LunrConfig.from_storage_conf()
        # If no time provided, use current time
        timestamp = timestamp or time()
        # Init our helpers
        volume = VolumeHelper(conf)
        backup = BackupHelper(conf)

        try:
            # Create the snapshot
            snapshot = volume.create_snapshot(src, id, timestamp)

            # For testing non-snapshot speeds
            # snapshot = volume.get(src)
            # snapshot['backup_id'] = id
            # snapshot['origin'] = src
            # snapshot['timestamp'] = 1338410885.0
            # del snapshot['volume']

            print("Created snap-shot: ", pprint(snapshot))

            with self.timeit(snapshot['size']):
                # Backup the snapshot
                print("Starting Backup")
                backup.save(snapshot, id)

        finally:
            # Delete the snapshot if it was created
            if 'snapshot' in locals():
                self._remove_volume(snapshot['path'])

    @opt('id', help="volume id to identify the new volume")
    @opt('--src', help="volume id the backup was created for", required=True)
    @opt('--backup', help="backup id to create the clone from", required=True)
    @opt('--size', help="new volume size (default: src volume size)")
    def clone(self, id=None, src=None, backup=None, size=None):
        """
        This runs a clone job outside of the storage api,
        which is useful for performance testing backup restores
        (Example: storage tools clone volume-clone
          --backup volume-backup --src volume-original)
        """
        # Set basic Logging
        logging.basicConfig()
        # Get the lunr logger
        log = logger.get_logger()
        # Output Debug level info
        log.logger.setLevel(logging.DEBUG)
        # Load the local storage configuration
        conf = LunrConfig.from_storage_conf()
        # Init the volume helper
        volume = VolumeHelper(conf)

        # Attempt to figure out the original volume size
        size = size or str(volume.get(src)['size'] / 1073741824)
        # Size is in gigs
        if not re.match('G', size):
            size = size + 'G'
        # Create a tag to apply to the lvm volume
        tag = encode_tag(source_volume_id=src, backup_id=backup)
        # Create the volume
        execute('lvcreate', volume.volume_group,
                name=id, size=size, addtag=tag)
        # Get info for the newly created volume
        new = volume.get(id)

        with self.timeit():
            print("Starting Backup")
            # Restore volume from the backup
            volume.clone(new, src, backup)
