"""

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import dateutil.parser
from .exceptions import Forbidden, HTTPException
# Imports go here.


class Status:
    class Active(object):
        pass

    class New(object):
        pass

    class Off(object):
        pass

    class Archive(object):
        pass

    class Other(object):
        pass
# A class with a bunch of statuses in.


class Type:
    class Snapshot(object):
        pass

    class Backup(object):
        pass

    class Other(object):
        pass
# A class with a bunch of types in.


class NetworkType:
    class Public(object):
        pass

    class Private(object):
        pass

    class Other(object):
        pass
# A class with a bunch of network types in.


class Kernel(object):
    __slots__ = ["id", "name", "version"]

    def __init__(self, kernel_json):
        if not kernel_json:
            self.id = None
            self.name = None
            self.version = None
            return

        self.id = kernel_json.get('id')
        self.name = kernel_json.get('name')
        self.version = kernel_json.get('version')
# A kernel object.


class Image(object):
    __slots__ = [
        "id", "name", "distribution", "slug",
        "public", "regions", "created_at", "type",
        "min_disk_size", "size_gigabytes"
    ]

    def __init__(self, image_json):
        self.id = image_json['id']
        self.name = image_json['name']
        self.distribution = image_json['distribution']
        self.slug = image_json['slug']
        self.public = image_json['public']
        self.regions = image_json['regions']
        self.created_at = dateutil.parser.parse(
            image_json['created_at']
        )

        if image_json['type'] == "snapshot":
            self.type = Type.Snapshot
        elif image_json['type'] == "backup":
            self.type = Type.Backup
        else:
            self.type = Type.Other

        self.min_disk_size = image_json['min_disk_size']
        self.size_gigabytes = image_json['size_gigabytes']
# A image object.


class Network(object):
    __slots__ = [
        "ip_address", "netmask", "gateway", "type",
        "ipv4"
    ]

    def __init__(self, _json, ipv4):
        self.ipv4 = ipv4
        self.ip_address = _json['ip_address']
        self.netmask = _json['netmask']
        self.gateway = _json['gateway']

        _type = _json['type']
        if _type == "public":
            self.type = NetworkType.Public
        elif _type == "private":
            self.type = NetworkType.Private
        else:
            self.type = NetworkType.Other
# A singular network object.


class Networks(object):
    __slots__ = ["ipv4", "ipv6"]

    def __init__(self, networks_json):
        self.ipv4 = [
            Network(n, True) for n in networks_json['v4']
        ]
        self.ipv6 = [
            Network(n, False) for n in networks_json['v6']
        ]
# A networks object.


class Region(object):
    __slots__ = [
        "name", "slug", "sizes",
        "features", "available"
    ]

    def __init__(self, region_json):
        self.name = region_json.get('name')
        self.slug = region_json.get('slug')
        self.sizes = region_json.get('sizes')
        self.features = region_json.get('features')
        self.available = region_json.get('available')
# A region object.


class Droplet(object):
    __slots__ = [
        "id", "name", "memory", "vcpus",
        "disk", "locked", "status", "kernel",
        "created_at", "features", "backup_ids",
        "snapshot_ids", "image", "volume_ids",
        "size", "networks", "region", "tags",
        "client"
    ]

    def __init__(self, client, droplet_json):
        self.client = client
        self.id = droplet_json['id']
        self.name = droplet_json['name']
        self.memory = droplet_json['memory']
        self.vcpus = droplet_json['vcpus']
        self.disk = droplet_json['disk']
        self.locked = droplet_json['locked']

        status = droplet_json['status']
        if status == "active":
            self.status = Status.Active
        elif status == "new":
            self.status = Status.New
        elif status == "off":
            self.status = Status.Off
        elif status == "archive":
            self.status = Status.Archive
        else:
            self.status = Status.Other

        self.kernel = Kernel(
            droplet_json['kernel']
        )

        self.created_at = dateutil.parser.parse(
            droplet_json['created_at']
        )

        self.features = droplet_json['features']
        self.backup_ids = droplet_json['backup_ids']
        self.snapshot_ids = droplet_json['snapshot_ids']

        self.image = Image(
            droplet_json['image']
        )

        self.volume_ids = droplet_json['volume_ids']
        self.size = droplet_json['size_slug']

        self.networks = Networks(
            droplet_json['networks']
        )

        self.region = Region(
            droplet_json['region']
        )

        self.tags = droplet_json['tags']

    async def delete(self):
        cli = self.client
        response = await cli.v2_request(
            "DELETE", f"droplets/{self.id}"
        )
        if isinstance(response, tuple):
            response = response[0]
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 204:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True

    async def update(self):
        model = self.client.droplet_model(
            id=self.id
        )
        try:
            return await model.find_one()
        except BaseException:
            return
# A droplet object.
