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

import aiohttp
import asyncio
from .exceptions import Forbidden, HTTPException, CannotCreateDroplet
from .abc import Droplet
# Imports go here.


class _DropletModel:
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
                        if key == "region":
                            if self.kwargs[key] == droplet.region.slug:
                                result = True
                            else:
                                break
                        elif key == "image":
                            if self.kwargs[key] == droplet.image.slug:
                                result = True
                            else:
                                break
                        elif self.kwargs[key] == droplet.__getattribute__(key):
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
                        if self.kwargs[key] != droplet.__getattribute__(key):
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
                        if key == "region":
                            if self.kwargs[key] == droplet.region.slug:
                                result = True
                            else:
                                break
                        elif key == "image":
                            if self.kwargs[key] == droplet.image.slug:
                                result = True
                            else:
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
            "region": self.kwargs['region'],
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


class Client:
    def __init__(self, api_key):
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
    # Runs a API V2 request.

    def droplet_model(
            self, id=None, name=None, size=None, locked=None,
            status=None, tags=None, region=None, image=None,
            user_init=None, ssh_keys=None
    ):
        return _DropletModel(
            self, id, name, size, locked,
            region, status, tags, image,
            user_init, ssh_keys
        )
    # Getting around language limitations.
