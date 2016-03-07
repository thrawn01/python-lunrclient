## LunrClient

An HTTP Client for use with the Lunr Storage Backend for Cinder

## Installation

    $ pip install python-lunrclient

## Usage

This package provides 2 command line tools `lunr` an inteface to the lunr
API and `storage` an interface to the storage API.

#### Lunr API commandline usage

    $ lunr -h
    Usage: lunr <command> [-h]

    Command line interface to the lunr api

    Available Commands:
       node
       account
       volume
       export
       env
       backup

#### Storage API commandline usage

    $ storage -h
    -- Warning: Failed to load tools module, Missing dependency?
    Usage: storage <command> [-h]

    Command line interface to the lunr storage api

    Available Commands:
       volume
       status
       export
       backup
       env

Both `lunr` and `storage` can use environment variables for convenience. 

Use `lunr env` and `storage env` to list environment variables that are used.

Currently the following are supported:

    export OS_TENANT_NAME='thrawn'
    export LUNR_ADMIN='admin'
    export LUNR_TENANT_ID='admin'
    export LUNR_STORAGE_URL='http://localhost:8081'
    export LUNR_API_URL='http://localhost:8080'

## Lunr API Examples

Create a 1 gig volume with a uuid for a name and use the default volume type:

    $ lunr volume create 1

List the available volumes for `OS_TENANT_NAME`:

    $ lunr volume list

Delete a volume:

    $ lunr volume delete my-volume

## Storage API Examples

Create a 1 gig volume with a uuid for a name:

    $ storage volume create 1

List the available volumes on the storage node:

    $ storage volume list

Delete a volume:

    $ storage volume delete my-volume

## Storage Tools

There are some additional storage server tools that are only available when run on the storage node:

    $ storage tools -h
    Usage: storage tools <command> [-h]

    A collection of misc Storage Node tools

    Available Commands:
       read
       randomize
       clone
       write
       backup
