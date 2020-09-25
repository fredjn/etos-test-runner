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
"""IUT monitoring module."""
from etos_lib.lib.config import Config

# TODO: Get this from environment provider


class IutMonitoring:
    """Helper class for monitoring IuT health statistics."""

    def __init__(self, iut):
        """Initialize monitoring.

        :param iut: IUT object to monitor.
        :type iut: :obj:`etr.lib.iut.Iut`
        """
        self.iut = iut
        self.config = Config()

    def start_monitoring(self):
        """Start monitoring IUT."""

    def stop_monitoring(self):
        """Stop monitoring IUT."""
