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

import abc
import dateutil.parser
from .exceptions import Forbidden, HTTPException, CannotCreateDroplet,\
    CannotCreateLoadBalancer
import asyncio
# Imports go here.


class Status(abc.ABC):
    class Active(object):
        pass

    class New(object):
        pass

    class Off(object):
        pass

    class Archive(object):
        pass

    class Warning(object):
        pass

    class Locked(object):
        pass

    class Other(object):
        __slots__ = ["status"]

        def __init__(self, status):
            self.status = status
# A class with a bunch of statuses in.


class Type(abc.ABC):
    class Snapshot(object):
        pass

    class Backup(object):
        pass

    class Other(object):
        pass
# A class with a bunch of types in.


class NetworkType(abc.ABC):
    class Public(object):
        pass

    class Private(object):
        pass

    class Other(object):
        pass
# A class with a bunch of network types in.


class Kernel(abc.ABC):
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


class Image(abc.ABC):
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


class Network(abc.ABC):
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


class Networks(abc.ABC):
    __slots__ = ["ipv4", "ipv6"]

    def __init__(self, networks_json):
        self.ipv4 = [
            Network(n, True) for n in networks_json['v4']
        ]
        self.ipv6 = [
            Network(n, False) for n in networks_json['v6']
        ]
# A networks object.


class Region(abc.ABC):
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


class Droplet(abc.ABC):
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
            self.status = Status.Other(status)

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

    async def add_to_load_balancer(self, load_balancer):
        await load_balancer.add_droplets(self)

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

    async def enable_backups(self):
        response, _json = await self.client.v2_request(
            "POST", f"droplets/{self.id}/actions", {
                "type": "enable_backups"
            }
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True

    async def disable_backups(self):
        response, _json = await self.client.v2_request(
            "POST", f"droplets/{self.id}/actions", {
                "type": "disable_backups"
            }
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True

    async def reboot(self):
        response, _json = await self.client.v2_request(
            "POST", f"droplets/{self.id}/actions", {
                "type": "reboot"
            }
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True

    async def power_cycle(self):
        response, _json = await self.client.v2_request(
            "POST", f"droplets/{self.id}/actions", {
                "type": "power_cycle"
            }
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True

    async def shutdown(self):
        response, _json = await self.client.v2_request(
            "POST", f"droplets/{self.id}/actions", {
                "type": "shutdown"
            }
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True

    async def power_off(self):
        response, _json = await self.client.v2_request(
            "POST", f"droplets/{self.id}/actions", {
                "type": "power_off"
            }
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True

    async def power_on(self):
        response, _json = await self.client.v2_request(
            "POST", f"droplets/{self.id}/actions", {
                "type": "power_on"
            }
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True

    async def restore(self, image_id: int):
        response, _json = await self.client.v2_request(
            "POST", f"droplets/{self.id}/actions", {
                "type": "restore",
                "image": image_id
            }
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        return True
# A droplet object.


class DropletModel(abc.ABC):
    def __init__(
        self, client, id=None, name=None,
        size=None, locked=None, region=None,
        status=None, tags=None, image=None,
        user_init=None, ssh_keys=None
    ):
        self.user_init = user_init
        self.ssh_keys = ssh_keys
        self.client = client
        self.kwargs = {}
        possible_args = [
            [id, "id"], [name, "name"],
            [size, "size"], [locked, "locked"],
            [status, "status"], [tags, "tags"],
            [region, "region"], [image, "image"]
        ]
        for arg in possible_args:
            if arg[0] is not None:
                self.kwargs[arg[1]] = arg[0]
    # Initialises the model.

    async def find_one(self):
        if "id" in self.kwargs:
            # We'll get this droplet by ID.
            response, _json = await self.client.v2_request(
                "GET", f"droplets/{self.kwargs['id']}"
            )
            if response.status == 403:
                raise Forbidden(
                    "Credentials invalid."
                )
            elif response.status == 404:
                return
            elif response.status != 200:
                raise HTTPException(
                    f"Returned the status {response.status}."
                )
            else:
                droplet = Droplet(
                    self.client, _json['droplet']
                )

                for key in self.kwargs:
                    if key != "id":
                        if self.kwargs[key] != droplet.__getattribute__(key):
                            return

                return droplet

        # We'll have to search all droplets.
        response, _json = await self.client.v2_request(
            "GET", "droplets"
        )

        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 200:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        else:
            for d in _json['droplets']:
                droplet = Droplet(self.client, d)
                result = False
                if len(self.kwargs) == 0:
                    result = True
                else:
                    for key in self.kwargs:
                        if self.kwargs[key] == droplet.__getattribute__(key):
                            result = True
                        else:
                            break
                if result:
                    return droplet
    # Tries to get a droplet matching the model. If it can't, it returns None.

    async def find_many(self):
        if "id" in self.kwargs:
            # We'll get this droplet by ID.
            response, _json = await self.client.v2_request(
                "GET", f"droplets/{self.kwargs['id']}"
            )
            if response.status == 403:
                raise Forbidden(
                    "Credentials invalid."
                )
            elif response.status == 404:
                return
            elif response.status != 200:
                raise HTTPException(
                    f"Returned the status {response.status}."
                )
            else:
                droplet = Droplet(
                    self.client, _json['droplet']
                )

                for key in self.kwargs:
                    if key != "id":
                        if key == "tags":
                            if self.kwargs[key] not in droplet.__getattribute__(key):
                                return
                        elif self.kwargs[key] != droplet.__getattribute__(key):
                            return

                yield droplet
                return

        # We'll have to search all droplets.
        response, _json = await self.client.v2_request(
            "GET", "droplets"
        )

        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 200:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        else:
            for d in _json['droplets']:
                droplet = Droplet(self.client, d)
                result = False
                if len(self.kwargs) == 0:
                    result = True
                else:
                    for key in self.kwargs:
                        if key == "tags":
                            if self.kwargs[key] not in droplet.__getattribute__(key):
                                break
                        elif self.kwargs[key] == droplet.__getattribute__(key):
                            result = True
                        else:
                            break
                if result:
                    yield droplet
    # Tries to make a generator of droplets matching the model. If it can't, it returns None.

    async def create(self, wait_for=True):
        if "size" not in self.kwargs:
            raise CannotCreateDroplet(
                "Size not found in your model."
            )
        elif "name" not in self.kwargs:
            raise CannotCreateDroplet(
                "Name not found in your model."
            )
        elif "region" not in self.kwargs:
            raise CannotCreateDroplet(
                "Region not found in your model."
            )

        to_send = {
            "size": self.kwargs['size'],
            "name": self.kwargs['name'],
            "region": self.kwargs['region'].slug,
            "image": self.kwargs['image']
        }

        if self.ssh_keys:
            to_send['ssh_keys'] = self.ssh_keys

        if self.user_init:
            to_send['user_data'] = self.user_init

        response, _json = await self.client.v2_request(
            "POST", "droplets", to_send
        )

        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 202:
            raise HTTPException(
                f"Returned the status {response.status}."
            )

        if not wait_for:
            return Droplet(self.client, _json['droplet'])

        _id = _json['droplet']['id']

        while True:
            await asyncio.sleep(1)
            response, _json = await self.client.v2_request(
                "GET", f"droplets/{_id}"
            )
            if _json['droplet']['status'] == "active":
                return Droplet(
                    self.client, _json['droplet']
                )
    # Creates a droplet.


class ForwardingRule(abc.ABC):
    __slots__ = [
        "entry_protocol", "entry_port",
        "target_protocol", "target_protocol",
        "certificate_id", "tls_passthrough"
    ]

    def __init__(self, rule_json):
        self.entry_protocol = rule_json[
            'entry_protocol'
        ]
        self.entry_port = rule_json[
            'entry_port'
        ]
        self.target_protocol = rule_json[
            'target_protocol'
        ]
        self.certificate_id = rule_json[
            'certificate_id'
        ] if rule_json['certificate_id']\
            != "" else None
        self.tls_passthrough = rule_json[
            'tls_passthrough'
        ]
        self.json = rule_json


class HealthCheck(abc.ABC):
    __slots__ = [
        "protocol", "port", "path",
        "check_interval_seconds",
        "response_timeout_seconds",
        "unhealthy_threshold",
        "healthy_threshold"
    ]

    def __init__(self, health_json):
        self.protocol = health_json[
            'protocol'
        ]
        self.port = health_json['port']
        self.path = health_json['path']
        self.check_interval_seconds =\
            health_json['check_interval_seconds']
        self.response_timeout_seconds =\
            health_json['response_timeout_seconds']
        self.unhealthy_threshold = health_json[
            'unhealthy_threshold'
        ]
        self.healthy_threshold = health_json[
            'healthy_threshold'
        ]


class StickySessions(abc.ABC):
    __slots__ = [
        "type", "cookie_name",
        "cookie_ttl_seconds"
    ]

    def __init__(self, session_json):
        self.type = session_json['type']
        self.cookie_name = session_json.get(
            "cookie_name"
        )
        self.cookie_ttl_seconds = session_json.get(
            "cookie_ttl_seconds"
        )


class LoadBalancer(abc.ABC):
    __slots__ = [
        "client", "id", "ip", "algorithm",
        "status", "created_at", "forwarding_rules",
        "health_check", "sticky_sessions", "region",
        "features", "available", "tag", "droplet_ids",
        "redirect_http_to_https"
    ]

    def __init__(self, client, balancer_json):
        self.client = client
        self.id = balancer_json['id']
        self.ip = balancer_json['ip']
        self.algorithm = balancer_json['algorithm']
        self.status = balancer_json['status']
        self.created_at = dateutil.parser.parse(
            balancer_json['created_at']
        )
        self.forwarding_rules = [
            ForwardingRule(r) for r in
            balancer_json['forwarding_rules']
        ]
        self.health_check = HealthCheck(
            balancer_json['health_check']
        )
        self.sticky_sessions = StickySessions(
            balancer_json['sticky_sessions']
        )
        self.region = Region(
            balancer_json['region']
        )
        self.tag = balancer_json['tag'] if balancer_json['tag']\
            != "" else None
        self.droplet_ids = balancer_json['droplet_ids']
        self.redirect_http_to_https = balancer_json[
            'redirect_http_to_https'
        ]

    async def update(self):
        model = self.client.load_balancer_model(
            id=self.id
        )
        try:
            return await model.find_one()
        except BaseException:
            return

    async def add_droplets(
        self, *droplets: Droplet
    ):
        d_ids = [
            d.id for d in droplets
        ]
        response = await self.client.v2_request(
            "POST", "load_balancers/load_balancers/"
            f"{self.id}/droplets",
            {
                "droplet_ids": d_ids
            }
        )
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

    async def delete(self):
        cli = self.client
        response = await cli.v2_request(
            "DELETE", f"load_balancers/{self.id}"
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

    async def add_forwarding_rules(
        self, *rules: ForwardingRule
    ):
        _j = {
            "forwarding_rules": [
                f.json for f in rules
            ]
        }
        response = self.client.v2_request(
            "POST", f"load_balancers/{self.id}"
            "/forwarding_rules", _j
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status != 204:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
    # Adds a set of forwarding rules.


class LoadBalancerModel(abc.ABC):
    def __init__(
        self, client, id=None, name=None, status=None,
        ip=None, algorithm=None, region=None, tag=None,
        redirect_http_to_https=None, droplets=None,
        forwarding_rules=None
    ):
        self.client = client
        self.kwargs = {}
        possible_args = [
            [id, "id"], [name, "name"],
            [ip, "ip"], [redirect_http_to_https,
                         "redirect_http_to_https"],
            [status, "status"], [tag, "tag"],
            [region, "region"], [algorithm,
                                 "algorithm"],
            [forwarding_rules, "forwarding_rules"]
        ]
        for arg in possible_args:
            if arg[0] is not None:
                self.kwargs[arg[1]] = arg[0]
        if droplets:
            self.kwargs['droplets'] = []
            for d in droplets:
                try:
                    self.kwargs['droplet_ids'].append(d.id)
                except AttributeError:
                    self.kwargs['droplet_ids'].append(d)
    # Initialises the model.

    async def find_one(self):
        if "id" in self.kwargs:
            # We'll get this load balancer by ID.
            response, _json = await self.client.v2_request(
                "GET", f"load_balancers/{self.kwargs['id']}"
            )
            if response.status == 403:
                raise Forbidden(
                    "Credentials invalid."
                )
            elif response.status == 404:
                return
            elif response.status != 200:
                raise HTTPException(
                    f"Returned the status {response.status}."
                )
            else:
                balancer = LoadBalancer(
                    self.client, _json['load_balancer']
                )

                for key in self.kwargs:
                    if key != "id":
                        if key == "forwarding_rules":
                            if self.kwargs[key] not in balancer.__getattribute__(key):
                                return
                        elif self.kwargs[key] != balancer.__getattribute__(key):
                            return

                return balancer

        # We'll have to search all load balancers.
        response, _json = await self.client.v2_request(
            "GET", "load_balancers"
        )

        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 200:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        else:
            for d in _json['load_balancers']:
                balancer = LoadBalancer(self.client, d)
                result = False
                if len(self.kwargs) == 0:
                    result = True
                else:
                    for key in self.kwargs:
                        if key == "forwarding_rules":
                            if self.kwargs[key] not in balancer.__getattribute__(key):
                                return
                        elif self.kwargs[key] != balancer.__getattribute__(key):
                            return
                        else:
                            break
                if result:
                    return balancer
    # Tries to get a droplet matching the model. If it can't, it returns None.

    async def find_many(self):
        if "id" in self.kwargs:
            # We'll get this droplet by ID.
            response, _json = await self.client.v2_request(
                "GET", f"load_balancers/{self.kwargs['id']}"
            )
            if response.status == 403:
                raise Forbidden(
                    "Credentials invalid."
                )
            elif response.status == 404:
                return
            elif response.status != 200:
                raise HTTPException(
                    f"Returned the status {response.status}."
                )
            else:
                balancer = LoadBalancer(
                    self.client, _json['load_balancer']
                )

                for key in self.kwargs:
                    if key != "id":
                        if key == "forwarding_rules":
                            if self.kwargs[key] not in balancer.__getattribute__(key):
                                return
                        elif self.kwargs[key] != balancer.__getattribute__(key):
                            return

                yield balancer
                return

        # We'll have to search all load balancers.
        response, _json = await self.client.v2_request(
            "GET", "load_balancers"
        )

        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status == 404:
            return
        elif response.status != 200:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        else:
            for b in _json['load_balancers']:
                balancer = LoadBalancer(self.client, b)
                result = False
                if len(self.kwargs) == 0:
                    result = True
                else:
                    for key in self.kwargs:
                        if key == "forwarding_rules":
                            if self.kwargs[key] not in balancer.__getattribute__(key):
                                break
                        elif self.kwargs[key] == balancer.__getattribute__(key):
                            result = True
                        else:
                            break
                if result:
                    yield balancer
    # Tries to make a generator of droplets matching the load balancers. If it can't, it returns None.

    async def create(self):
        if "name" not in self.kwargs:
            raise CannotCreateLoadBalancer(
                "Name not found in your model."
            )
        elif "region" not in self.kwargs:
            raise CannotCreateLoadBalancer(
                "Region not found in your model."
            )
        elif "forwarding_rules" not in self.kwargs:
            raise CannotCreateLoadBalancer(
                "Forwarding rules not found "
                "in your model."
            )

        to_send = {
            "name": self.kwargs['name'],
            "region": self.kwargs['region'].slug,
            "forwarding_rules": [f.json for f in
                self.kwargs['forwarding_rules']]
        }

        if "droplet_ids" in self.kwargs:
            to_send['droplet_ids'] =\
                self.kwargs['droplet_ids']

        response, _j = await self.client.v2_request(
            "GET", "load_balancers",
            to_send
        )

        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status != 200:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        else:
            return LoadBalancer(self.client, _j)
    # Creates a load balancer.


class AccountStatus(abc.ABC):
    __slots__ = [
        "status", "message"
    ]

    def __init__(
        self, status, message
    ):
        if status == "active":
            self.status = Status.Active
        elif status == "warning":
            self.status = Status.Warning
        elif status == "locked":
            self.status = Status.Locked

        self.message = message
# A class for a DigitalOcean account status.


class User(abc.ABC):
    __slots__ = [
        "droplet_limit", "floating_ip_limit",
        "email", "uuid", "email_verified",
        "status"
    ]

    def __init__(self, user_json):
        self.droplet_limit = user_json[
            'droplet_limit'
        ]
        self.floating_ip_limit = user_json[
            'floating_ip_limit'
        ]
        self.email = user_json['email']
        self.uuid = user_json['uuid']
        self.email_verified = user_json[
            'email_verified'
        ]
        self.status = AccountStatus(
            user_json['status'],
            user_json['status_message']
        )
# A class for a DigitalOcean user.
