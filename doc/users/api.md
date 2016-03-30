<!--
Copyright 2016, 2017 IBM Corp.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->
# Structure

The API follow a REST-like structure, with the following characteristics:

- endpoints are in the form `/resource_type/resource_name/method`
- the request (for POST and PUT) and response bodies are in json format

Many requests accept an 'extensions' field and its content is specific to the hypervisor or guest type in use. For available parameters check the document corresponding to the hypervisor or guest type you want to know.

## Authentication method

TODO

# Endpoints

## *Hypervisors*

All endpoints below are executed within the context of the hypervisor system

- [Start/IPL a guest](#startipl-a-guest)
- [Stop/shutdown a guest](#stopshutdown-a-guest)
- [Hotplug/unplug resources to/from a guest](#hotplugunplug-resources-tofrom-a-guest)
- [Get guest information](#get-guest-information)
- [Open guest console](#open-guest-console)

## *Guests*

All endpoints below are executed within the context of the guest operating system

- [Soft stop guest](#soft-stop-guest)
- [Hotplug/unplug resources](#hotplugunplug-resources)
- [Open a session](#open-a-session)
- [Pull files from guest](#pull-files-from-guest)
- [Push files to guest](#push-files-to-guest)
- [Install packages](#install-packages)

## *Tasks*

Endpoints related to the tasks queue

- [List tasks](#list-tasks)
- [Get task information](#get-task-information)
- [Cancel a task](#cancel-a-task)

## Start/IPL a guest

`PUT /hypervisors/{system_name}/guests/{guest_name}/start`

**Example request:**

```javascript
{
 'hypervisor': {
    'hostname': 'hostname|ipaddress',
    'username': 'user',
    'password': 'password'
    'type': 'hmc_rest|hmc_snipl|zvm|kvm|docker',
 },
 'guest': {
    'resources': {
        'cpu': cpu_qty,
        'memory': mem_qty,
        'disks': [],
        'netcards': [],
    },
    'boot': {
        'method': 'disk|network',
        'device': 'disk_name|url',
    },
 },
 'extensions': {}
}
```

**Example response:**
```javascript
{
 'result': 'ok|error',
 'message': 'error explanation in case of error',
 'taskid': 'hash to follow progress if accepted'
}
```

## Stop/shutdown a guest

`PUT /hypervisors/{system_name}/guests/{guest_name}/stop`

**Example request:**
```javascript
{
 'hypervisor': {
    'hostname': 'hostname|ipaddress',
    'username': 'user',
    'password': 'password',
    'type': 'hmc_rest|hmc_snipl|zvm|kvm|docker',
 },
 'extensions': {}
}
```

**Example response:**
```javascript
{
 'result': 'ok|error',
 'message': 'error explanation in case of error',
 'taskid': 'hash to follow progress if accepted'
}
```

## Hotplug/unplug resources to/from a guest

`PUT /hypervisors/{hypervisor_name}/guests/{guest_name}/hotplug`

**Example request:**
```javascript
{
 'hypervisor': {
    'hostname': 'hostname|ipaddress',
    'username': 'user',
    'password': 'password'
    'type': 'hmc_rest|hmc_snipl|zvm|kvm|docker',
 },
 'guest': {
    'method': 'attach|detach',
    'resources': {
        'cpu': qty_to_add,
        'memory': qty_to_add,
        'disks': [],
        'netcards': [],
    }
 },
 'extensions': {}
}
```

**Example response:**
```javascript
{
 'result': 'ok|error',
 'message': 'error explanation in case of error',
 'taskid': 'hash to follow progress if accepted'
}
```

## Get guest information

`POST /hypervisors/{hypervisor_name}/guests/{guest_name}/info`

**Example request:**
```javascript
{
 'hypervisor': {
    'hostname': 'hostname|ipaddress',
    'username': 'user',
    'password': 'password'
    'type': 'hmc_rest|hmc_snipl|zvm|kvm|docker',
 },
 'extensions': {}
}
```

**Example response:**
```javascript
{
 'result': 'ok|error',
 'message': 'error explanation in case of error',
 'info': {
    'state': 'online|offline',
    'extensions': {},
 }
}
```
## Open guest console

`POST /hypervisors/{hypervisor_name}/guests/{guest_name}/console`

This will open a websocket for sending input and receiving output directly from the guest console

**Example request:**
```javascript
{
 'hypervisor': {
    'hostname': 'hostname|ipaddress',
    'username': 'user',
    'password': 'password'
    'type': 'hmc_rest|hmc_snipl|zvm|kvm|docker',
 },
 'extensions': {}
}
```

**Example response:**
```javascript
# TODO
```

## Soft stop guest

`PUT /guests/{guest_name}/stop`

**Example request:**
```javascript
{
 'guest': {
    'hostname': 'hostname|ipaddress'
    'username': 'user',
    'password': 'password',
    'type': 'linux|cms',
 },
 'extensions': {}
}
```

**Example response:**
```javascript
{
 'result': 'ok|error',
 'message': 'error explanation in case of error',
 'taskid': 'hash to follow progress if accepted'
}
```

## Hotplug/unplug resources

`PUT /guests/{guest_name}/hotplug`

**Example request:**
```javascript
{
 'guest': {
    'hostname': 'hostname|ipaddress'
    'username': 'user',
    'password': 'password',
    'type': 'linux|cms',
    'method': 'attach|detach',
    'resources': {
        'cpu': qty_to_add,
        'memory': qty_to_add,
        'disks': [],
        'netcards': [],
    }
 },
 'extensions': {}
}
```

**Example response:**
```javascript
{
 'result': 'ok|error',
 'message': 'error explanation in case of error',
 'taskid': 'hash to follow progress if accepted'
}
```

## Open a session

`POST /guests/{guest_name}/session`

This will open a websocket for sending input and receiving output directly from a session on the operating system

**Example request:**
```javascript
{
 'guest': {
    'hostname': 'hostname|ipaddress'
    'username': 'user',
    'password': 'password',
    'type': 'linux|cms',
 },
 'extensions': {}
}
```

**Example response:**
```javascript
# TODO
```

## Pull files from guest

`POST /guests/{guest_name}/pull`

**Example request:**
```javascript
{
 'guest': {
    'hostname': 'hostname|ipaddress'
    'username': 'user',
    'password': 'password',
    'type': 'linux|cms',
    'path': 'path_to_file_or_dir',
 },
 'extensions': {}
}
```

**Example response:**
```javascript
# TODO
```

## Push files to guest

`POST /guests/{guest_name}/push`

**Example request:**
```javascript
{
 'guest': {
    'hostname': 'hostname|ipaddress'
    'username': 'user',
    'password': 'password',
    'type': 'linux|cms',
    'path': 'target_path',
 },
 'extensions': {}
}
```

**Example response:**
```javascript
# TODO
```

## Install packages

`POST /guests/{guest_name}/install`

**Example request:**
```javascript
{
 'guest': {
    'hostname': 'hostname|ipaddress'
    'username': 'user',
    'password': 'password',
    'type': 'linux|cms',
    'packages': ['pkg1', 'pkg2'],
 },
 'extensions': {}
}
```

**Example response:**
```javascript
{
 'result': 'ok|error',
 'message': 'error explanation in case of error',
 'taskid': 'hash to follow progress if accepted'
}
```

## List tasks

`GET /tasks?state=active&hypervisor=kvm`

Possible filters are:

- state: active|done|failed
- hypervisor: hmc_rest|hmc_snipl|zvm|kvm|docker

**Example response:**
```javascript
{
 'tasks': [
    {
        'state': 'active',
        'id': 'hashxxx',
        'action': 'endpoint',
        'start': 'start_date',
        'end': null,
        'hypervisor': {
            'name': 'hypervisor_name',
            'hostname': 'hostname',
            'type': 'kvm'
        },
        'guest': {}
    },
    {
        'state': 'failed',
        'id': 'hashyyy',
        'action': 'endpoint',
        'start': 'start_date',
        'end': 'end_date',
        'hypervisor': {},
        'guest': {
            'name': 'guest_name',
            'hostname': 'hostname',
            'type': 'kvm'
        }
    }
 ] },
}
```

## Get task information

`GET /tasks/{taskid}?offset=5&limit=50`

Possible parameters are:

- offset: which line to start fetching log messages
- limit: maximum number of lines to return

**Example response:**
```javascript
{
 'state': 'failed',
 'id': 'hashyyy',
 'action': 'endpoint',
 'start': 'start_date',
 'end': 'end_date',
 'hypervisor': {},
 'guest': {
    'name': 'guest_name',
    'hostname': 'hostname',
    'type': 'kvm'
    },
 'messages': [
        {'date': 'datetime', 'loglevel': 'debug|info|error|warning', 'message': 'some message'},
        {'date': 'datetime2', 'loglevel': 'debug|info|error|warning', 'message': 'some message 2'},
 ]
}
```

## Cancel a task

`PUT /tasks/{taskid}/cancel`

**Example response:**
```javascript
{
 'result': 'ok|error',
 'message': 'error explanation in case of error',
 'taskid': 'hash to follow progress if accepted'
}
```
