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
from .abc import DropletModel
# Imports go here.


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
        return DropletModel(
            self, id, name, size, locked,
            region, status, tags, image,
            user_init, ssh_keys
        )
    # Getting around language limitations.
