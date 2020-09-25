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
"""Log handler test module."""
import os
import sys
import logging
import errno
from unittest import TestCase
from pathlib import Path
from mock import MagicMock, patch, call

from etos_test_runner.lib.logs import LogHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
LOGGER = logging.getLogger(__name__)

# pylint:disable=protected-access


def step(msg):
    """Test step printer."""
    LOGGER.info("STEP: %s", msg)


class TestLogHandler(TestCase):
    """Tests for the ETR log handler."""

    def setUp(self):
        """Initialize a log cleanup list."""
        self.logs = []

    def tearDown(self):
        """Cleanup all log files created."""
        for log in self.logs:
            try:
                os.remove(log)
            except OSError:
                print("Failed to remove logfile %r" % log)

    @patch("etos_test_runner.lib.logs.os.rename")
    def test_move_log_to_pre_upload_path(self, mock_os_rename):
        """Test that it is possible to move a file to pre-upload path.

        Approval criteria:
            - Log handler shall create a new log file in the pre-upload path.

        Test steps::
            1. Initialize log handler.
            2. Create a log file to move.
            3. Tell log handler to move log file to pre-upload path.
            4. Verify that a new log file was created.
        """
        step("Initialize log handler.")
        log_handler = LogHandler("1", "2", "3", MagicMock(), MagicMock())

        step("Create a log file to move.")
        input_filename = Path(os.path.join(BASE_DIR, "a_pretty_log_name.log"))
        input_filename.touch()
        self.logs.append(input_filename)

        expected_filename = Path(
            os.path.join(log_handler.pre_upload_path, "a_new_log_name.log")
        )

        log = {"name": expected_filename.name, "file": str(input_filename)}
        step("Tell log handler to move log file to pre-upload path.")
        log_handler._move_log_to_pre_upload_path(log)

        step("Verify that a new log file was created.")
        mock_os_rename.assert_called_once_with(
            str(input_filename), str(expected_filename.absolute())
        )

    @patch("etos_test_runner.lib.logs.os.rename")
    def test_move_log_to_pre_upload_path_already_exists(self, mock_os_rename):
        """Test that log handler will rename the log file when a log file with name already exists.

        Approval criteria:
            - Log handler shall create a new log file in the pre-upload path.

        Test steps::
            1. Initialize log handler.
            2. Create a log file to move.
            3. Create a log file in the pre-upload path with the same name as log file.
            4. Tell log handler to move log file to pre-upload path.
            5. Verify that a new log file was created.
        """
        step("Initialize log handler.")
        log_handler = LogHandler("1", "2", "3", MagicMock(), MagicMock())

        step("Create a log file to move.")
        input_filename = Path(os.path.join(BASE_DIR, "a_pretty_log_name.log"))
        input_filename.touch()
        self.logs.append(input_filename)

        step("Create a log file in the pre-upload path with the same name as log file.")
        already_exists = Path(
            os.path.join(log_handler.pre_upload_path, "a_new_log_name.log")
        )
        already_exists.parent.mkdir(parents=True, exist_ok=True)
        already_exists.touch()
        self.logs.append(already_exists)

        expected_filename = Path(
            os.path.join(log_handler.pre_upload_path, "1_a_new_log_name.log")
        )

        log = {"name": already_exists.name, "file": str(input_filename)}
        step("Tell log handler to move log file to pre-upload path.")
        log_handler._move_log_to_pre_upload_path(log)

        step("Verify that a new log file was created.")
        mock_os_rename.assert_called_once_with(
            str(input_filename), str(expected_filename.absolute())
        )

    @patch("etos_test_runner.lib.logs.os.rename")
    def test_move_log_to_pre_upload_path_too_long_filename(self, mock_os_rename):
        """Test that log handler will reduce the length of logfile filename if it's too long.

        Approval criteria:
            - Log handler shall create a new log file in the pre-upload path.

        Test steps::
            1. Initialize log handler.
            2. Create a log file to move.
            3. Tell log handler to move log file to pre-upload path with a too long name.
            4. Verify that a new log file was created.
        """
        step("Initialize log handler.")
        log_handler = LogHandler("1", "2", "3", MagicMock(), MagicMock())
        exception = OSError()
        exception.errno = errno.ENAMETOOLONG
        mock_os_rename.side_effect = exception, True

        step("Create a log file to move.")
        input_filename = Path(os.path.join(BASE_DIR, "a_pretty_log_name.log"))
        input_filename.touch()
        self.logs.append(input_filename)

        expected_filename = Path(
            os.path.join(log_handler.pre_upload_path, "{}.log".format("a" * 249))
        )

        log = {"name": "{}.log".format("a" * 290), "file": str(input_filename)}
        step(
            "Tell log handler to move log file to pre-upload path with a too long name."
        )
        log_handler._move_log_to_pre_upload_path(log)
        calls = [
            call(
                str(input_filename),
                os.path.join(log_handler.pre_upload_path, "{}.log".format("a" * 290)),
            ),
            call(str(input_filename), str(expected_filename.absolute())),
        ]

        step("Verify that a new log file was created.")
        mock_os_rename.assert_has_calls(calls)
