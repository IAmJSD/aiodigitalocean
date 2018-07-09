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

import os
import aiohttp
from .abc import DropletModel, LoadBalancerModel,\
    Region, Image, User, ForwardingRule, SSHKey
from .exceptions import EnvVariableNotFound, Forbidden,\
    HTTPException
# Imports go here.


def get_slug(_j):
    if not _j['slug']:
        return ""

    return _j['slug'].lower()
# Gets the slug.


class Client:
    def __init__(self, api_key):
        if api_key is None:
            try:
                self.api_key = os.environ[
                    'DIGITALOCEAN_API_KEY'
                ]
                return
            except KeyError:
                raise EnvVariableNotFound(
                    "None was specified to the client"
                    " for the API key. This means that"
                    " you need the environment variable"
                    " DIGITALOCEAN_API_KEY."
                )

        self.api_key = api_key
    # Initialises a client.

    async def v2_request(self, method, address, data=None):
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(
                    f"https://api.digitalocean.com/v2/{address}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    }
                ) as response:
                    try:
                        return response, (await response.json())
                    except aiohttp.client_exceptions.ContentTypeError:
                        return response
            elif method == "POST":
                async with session.post(
                    f"https://api.digitalocean.com/v2/{address}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    data=data
                ) as response:
                    try:
                        return response, (await response.json())
                    except aiohttp.client_exceptions.ContentTypeError:
                        return response
            elif method == "DELETE":
                async with session.delete(
                    f"https://api.digitalocean.com/v2/{address}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    }
                ) as response:
                    try:
                        return response, (await response.json())
                    except aiohttp.client_exceptions.ContentTypeError:
                        return response
            elif method == "PUT":
                async with session.put(
                    f"https://api.digitalocean.com/v2/{address}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    }
                ) as response:
                    try:
                        return response, (await response.json())
                    except aiohttp.client_exceptions.ContentTypeError:
                        return response
    # Runs a API V2 request.

    def droplet_model(
            self, id=None, name=None, size=None, locked=None,
            status=None, tags=None, region=None, image=None,
            user_init=None, ssh_keys=None
    ):
        return DropletModel(
            self, id, name, size, locked,
            region, status, tags, image,
            user_init, ssh_keys
        )
    # Creates a droplet model without having to specify the client.

    def load_balancer_model(
            self, id=None, name=None, status=None, ip=None,
            algorithm=None, region=None, tag=None,
            redirect_http_to_https=None, droplets=None
    ):
        return LoadBalancerModel(
            self, id, name, status, ip,
            algorithm, region, tag,
            redirect_http_to_https,
            droplets
        )
    # Creates a load balancer model without having to specify the client.

    async def get_region(self, region_slug):
        region_slug = region_slug.lower()
        resp, _j = await self.v2_request(
            "GET", "regions"
        )
        regions = _j['regions']
        for r in regions:
            if get_slug(r) == region_slug:
                return Region(r)
    # Gets the region by slug.

    async def get_image(self, image_slug):
        image_slug = image_slug.lower()
        resp, _j = await self.v2_request(
            "GET", "images?type=distribution"
        )
        images = _j['images']
        for i in images:
            if get_slug(i) == image_slug:
                return Image(i)
    # Gets the image by slug.

    async def get_user(self):
        response, _j = await self.v2_request(
            "GET", "account"
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
            return User(_j['account'])
    # Gets the DigitalOcean user for the person signed in.

    @staticmethod
    def create_forwarding_rule(
        entry_protocol, entry_port,
        target_protocol, target_port,
        certificate_id=None, tls_passthrough=None
    ):
        _j = {
            "entry_protocol": entry_protocol,
            "entry_port": entry_port,
            "target_protocol": target_protocol,
            "target_port": target_port
        }
        if certificate_id:
            _j['certificate_id'] = certificate_id
        else:
            _j['certificate_id'] = ""

        if tls_passthrough:
            _j['tls_passthrough'] = tls_passthrough
        else:
            _j['tls_passthrough'] = False

        return ForwardingRule(_j)
    # Creates a forwarding rule.

    async def get_ssh_key(self, key_name):
        response, _j = await self.v2_request(
            "GET", "account/keys"
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
            for key in _j['ssh_keys']:
                if key['name'] == key_name:
                    return SSHKey(self, key)
    # Gets a SSH key by name.

    async def ssh_keys(self):
        response, _j = await self.v2_request(
            "GET", "account/keys"
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
            for key in _j['ssh_keys']:
                yield SSHKey(self, key)
    # Gets all of the SSH keys.

    async def create_ssh_key(self, name, public_key):
        _j = {
            "name": name,
            "public_key": public_key
        }
        response, json = await self.v2_request(
            "POST", "account/keys", _j
        )
        if response.status == 403:
            raise Forbidden(
                "Credentials invalid."
            )
        elif response.status != 201:
            raise HTTPException(
                f"Returned the status {response.status}."
            )
        else:
            return SSHKey(self, json['ssh_key'])
    # Creates a SSH key.

    async def images(self):
        resp, _j = await self.v2_request(
            "GET", "images?type=distribution"
        )
        images = _j['images']
        for i in images:
            yield Image(i)
    # Gets all of the images.

    async def regions(self):
        resp, _j = await self.v2_request(
            "GET", "regions"
        )
        regions = _j['regions']
        for r in regions:
            yield Region(r)
    # Gets all of the regions.
