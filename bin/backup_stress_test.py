#! /usr/bin/env python

from __future__ import print_function

from lunrclient import StorageBackup, StorageVolume, LunrError
import time
import uuid
import sys
import os
import re


def dash(value):
    return re.sub('-', '--', value)

def get_dm_name(volume):
    path = volume.split('/')
    cow_device = "%s-%s" % (dash(path[2]), dash(path[3]))
    dm_name = "/".join(['', path[1], 'mapper', cow_device])
    return dm_name


def main():
    storage = StorageVolume(debug=True)
    backup = StorageBackup(debug=True)

    for i in range(0, 20):
        volume_id = str(uuid.uuid4())
        backup_id = str(uuid.uuid4())

        # Create a volume, then a backup of the volume
        print("++ Vol: %s Backup: %s ++" % (volume_id, backup_id))
        result = storage.create(volume_id, 1)
        result = backup.create(backup_id, volume_id, 1)

        # Wait until the storage node returns 404
        while(result):
            try:
                result = backup.get(backup_id, volume_id)
                os.system("ls %s*" % get_dm_name("/dev/lunr-volume/%s" % backup_id))
                time.sleep(1)
            except LunrError as e:
                if e.code != 404:
                    raise
                # storage node returned 404
                break

        # Show the snapshot created
        os.system("ls %s*" % get_dm_name("/dev/lunr-volume/%s" % volume_id))

        # Because storage node will return 404 before the backup actually
        # completes we have to list the backup and wait until it shows up
        while True:
            result = backup.list(volume_id)
            if backup_id in result.keys():
                break

        # Now delete the backup and wait until it goes away
        # (unable to use .get() as it will 404 even tho the backup exists)
        result = backup.delete(backup_id, volume_id)
        while(result):
            result = backup.list(volume_id)
            if backup_id not in result.keys():
                break

        # Attempt to delete the volume
        while True:
            try:
                result = storage.delete(volume_id)
                break
            except LunrError as e:
                # If we get 409, just try again
                if e.code != 409:
                    raise


if __name__ == "__main__":
    sys.exit(main())
