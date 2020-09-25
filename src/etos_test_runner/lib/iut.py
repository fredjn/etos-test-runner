# Copyright 2020 Axis Communications AB.
#
# For a full list of individual contributors, please see the commit history.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""IUT data structure module."""
import os
from packageurl import PackageURL


class Iut:  # pylint: disable=too-few-public-methods
    """Data object for IUTs."""

    def __init__(self, product):
        """Initialize.

        :param product: Dictionary to set attributes from.
                        Should be the response from pool plugin list.
        :type product: dict
        """
        try:
            self.load_environment(product.pop("environment"))
        except KeyError:
            pass
        try:
            self.prepare(product.pop("commands"))
        except KeyError:
            pass
        product["identity"] = PackageURL.from_string(product["identity"])
        for key, value in product.items():
            setattr(self, key, value)
        self._product_dict = product

    @staticmethod
    def load_environment(environment):
        """Load and set environment variables from IUT definition.

        :param environment: Environment variables to set.
        :type environment: dict
        """
        for key, value in environment.items():
            os.environ[key] = value

    def prepare(self, commands):
        """Prepare IUT and IUT environment for tests.

        :param commands: Commands to execute.
        :type commands: list
        """

    @property
    def as_dict(self):
        """Return IUT as a dictionary."""
        return self._product_dict

    def __repr__(self):
        """Represent IUT as string."""
        try:
            return self._product_dict.get("identity").to_string()
        except:  # noqa pylint:disable=bare-except
            return "Unknown"
