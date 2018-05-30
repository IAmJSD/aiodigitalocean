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
from .exceptions import Forbidden, HTTPException
from .abc import Droplet
# Imports go here.


class _DropletModel:
    def __init__(
        self, client, id=None, name=None,
        size=None, locked=None,
        status=None, tags=None
    ):
        self.client = client
        self.kwargs = {}
        possible_args = [
            [id, "id"], [name, "name"],
            [size, "size"], [locked, "locked"],
            [status, "status"], [tags, "tags"]
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
                for key in self.kwargs:
                    if self.kwargs[key] == droplet.__getattribute__(key):
                        result = True
                    else:
                        break
                if result:
                    return droplet
    # Tries to get a droplet matching the model. If it can't, it returns None.


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
                    return response, (await response.json())
            elif method == "POST":
                async with session.post(
                    f"https://api.digitalocean.com/v2/{address}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    data=data
                ) as response:
                    return response, (await response.json())
            elif method == "DELETE":
                async with session.delete(
                    f"https://api.digitalocean.com/v2/{address}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    }
                ) as response:
                    return response, (await response.json())
    # Runs a API V2 request.

    def DropletModel(
            self, id=None, name=None, size=None, locked=None,
            status=None, tags=None
    ):
        return _DropletModel(self, id, name, size, locked, status, tags)
    # Getting around language limitations.
