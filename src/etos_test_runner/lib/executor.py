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
"""ETR executor module."""
import os
import shlex
import logging
import signal
from pprint import pprint
from tempfile import mkdtemp
from etos_test_runner.test_regex import TEST_REGEX

BASE = os.path.dirname(os.path.abspath(__file__))


class TestCheckoutTimeout(TimeoutError):
    """Test checkout timeout exception."""


def _test_checkout_signal_handler(signum, frame):  # pylint:disable=unused-argument
    """Raise timeout error on test checkout."""
    raise TestCheckoutTimeout("Took too long to checkout test cases.")


class Executor:  # pylint: disable=too-many-instance-attributes
    """Execute a single test-case, -class, -module, -folder etc."""

    report_path = "test_output.log"
    test_name = ""
    current_test = None
    test_checkouts = {}
    logger = logging.getLogger("Executor")

    # pylint: disable=too-many-arguments
    def __init__(self, test, iut, etos):
        """Initialize.

        :param test: Test to execute.
        :type test: str
        :param iut: IUT to execute test on.
        :type iut: :obj:`etr.lib.iut.Iut`
        """
        self.test = test
        self.tests = {}

        self.test_environment_variables = {}
        self.test_command = None
        self.pre_test_execution = []
        self.test_command_input_arguments = {}
        self.checkout_command = []

        self.constraints = test.get("constraints", [])
        for constraint in self.constraints:
            if constraint.get("key") == "ENVIRONMENT":
                self.test_environment_variables = constraint.get("value")
            elif constraint.get("key") == "COMMAND":
                self.test_command = constraint.get("value")
            elif constraint.get("key") == "EXECUTE":
                self.pre_test_execution = constraint.get("value")
            elif constraint.get("key") == "PARAMETERS":
                self.test_command_input_arguments = constraint.get("value")
            elif constraint.get("key") == "CHECKOUT":
                self.checkout_command = constraint.get("value")

        self.test_name = test.get("testCase").get("id")
        self.test_id = test.get("id")
        self.iut = iut
        self.etos = etos
        self.context = self.etos.config.get("context")
        self.result = True

    def _checkout_tests(self, test_checkout):
        """Check out tests for this execution.

        :param test_checkout: Test checkout parameters from test suite.
        :type test_checkout: list
        """
        with open(os.path.join(BASE, "checkout.sh"), "w") as checkout_file:
            checkout_file.write('eval "$(pyenv init -)"\n')
            checkout_file.write("pyenv shell --unset\n")
            for command in test_checkout:
                checkout_file.write("{} || exit 1\n".format(command))

        signal.signal(signal.SIGALRM, _test_checkout_signal_handler)
        signal.alarm(60)
        try:
            checkout = os.path.join(BASE, "checkout.sh")
            success, output = self.etos.utils.call(
                ["/bin/bash", checkout], shell=True, wait_output=False
            )
        finally:
            signal.alarm(0)
        if not success:
            pprint(output)
            raise Exception("Could not checkout tests using '{}'".format(test_checkout))

    def test_directory(self, test_checkout):
        """Test directory for the test checkout.

        If a test directory does not already exist, generate it by calling the
        supplied command from test suite.
        If it does exist, just return that directory.

        :param test_checkout: Test checkout parameters from test suite.
        :type test_checkout: list
        :return: Folder where to execute a testcase
        :rtype: str
        """
        string_checkout = " ".join(test_checkout)
        if self.test_checkouts.get(string_checkout) is None:
            test_folder = mkdtemp(dir=os.getcwd())
            with self.etos.utils.chdir(test_folder):
                self._checkout_tests(test_checkout)
            self.test_checkouts[string_checkout] = test_folder
        return self.test_checkouts.get(string_checkout)

    def _build_test_command(self):
        """Build up the actual test command based on data from event."""
        executor = os.path.join(BASE, "executor.sh")
        test_command = ""
        parameters = []

        for parameter, value in self.test_command_input_arguments.items():
            if value == "":
                parameters.append(parameter)
            else:
                parameters.append("{}={}".format(parameter, value))

        test_command = "{} {} {} 2>&1".format(
            executor, self.test_command, " ".join(parameters)
        )
        return test_command

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, _type, value, traceback):
        """Exit context."""

    @staticmethod
    def _pre_execution(command):
        """Write pre execution command to a shell script.

        :param command: Environment and pre execution shell command to write to shell script.
        :type command: str
        """
        with open(os.path.join(BASE, "environ.sh"), "w") as environ_file:
            for arg in command:
                environ_file.write("{} || exit 1\n".format(arg))

    def _build_environment_command(self):
        """Build command for setting environment variables prior to execution.

        :return: Command to run pre execution.
        :rtype: str
        """
        environments = [
            "export {}={}".format(key, shlex.quote(value))
            for key, value in self.test_environment_variables.items()
        ]
        return environments + self.pre_test_execution

    def _triggered(self, test_name):
        """Send a test case triggered event.

        :param test_name: Name of test that is triggered.
        :type test_name: str
        :return: Test case triggered event created and sent.
        :rtype: :obj:`eiffellib.events.eiffel_test_case_triggered_event.EiffelTestCaseTriggeredEvent`  # pylint:disable=line-too-long
        """
        return self.etos.events.send_test_case_triggered(
            {"id": test_name}, self.iut.artifact, links={"CONTEXT": self.context}
        )

    def _started(self, test_name):
        """Send a testcase started event.

        :param test_name: Name of test that has started.
        :type test_name: str
        :return: Test case started event created and sent.
        :rtype: :obj:`eiffellib.events.eiffel_test_case_started_event.EiffelTestCaseStartedEvent`
        """
        triggered = self.tests[test_name].get("triggered")
        if triggered is None:
            return None
        return self.etos.events.send_test_case_started(
            triggered, links={"CONTEXT": self.context}
        )

    def _finished(self, test_name, result):
        """Send a testcase finished event.

        :param test_name: Name of test that is finished.
        :type test_name: str
        :param result: Result of test case.
        :type result: str
        :return: Test case finished event created and sent.
        :rtype: :obj:`eiffellib.events.eiffel_test_case_finished_event.EiffelTestCaseFinishedEvent`
        """
        triggered = self.tests[test_name].get("triggered")
        if triggered is None:
            return None

        if result == "ERROR":
            outcome = {"verdict": "FAILED", "conclusion": "INCONCLUSIVE"}
        elif result == "FAILED":
            outcome = {"verdict": "FAILED", "conclusion": "FAILED"}
        elif result == "SKIPPED":
            outcome = {
                "verdict": "PASSED",
                "conclusion": "SUCCESSFUL",
                "description": "SKIPPED",
            }
        else:
            outcome = {"verdict": "PASSED", "conclusion": "SUCCESSFUL"}
        return self.etos.events.send_test_case_finished(
            triggered, outcome, links={"CONTEXT": self.context}
        )

    def parse(self, line):
        """Parse test output in order to send test case events.

        :param line: Line to parse.
        :type line: str
        """
        if not isinstance(line, str):
            return
        test_name = TEST_REGEX["test_name"].findall(line)
        if test_name:
            self.current_test = test_name[0]
            self.tests.setdefault(self.current_test, {})
        if TEST_REGEX["triggered"].match(line):
            self.tests[self.current_test]["triggered"] = self._triggered(
                self.current_test
            )
        if TEST_REGEX["started"].match(line):
            self.tests[self.current_test]["started"] = self._started(self.current_test)
        if TEST_REGEX["passed"].match(line):
            self.tests[self.current_test]["finished"] = self._finished(
                self.current_test, "PASSED"
            )
        if TEST_REGEX["failed"].match(line):
            self.tests[self.current_test]["finished"] = self._finished(
                self.current_test, "FAILED"
            )
        if TEST_REGEX["error"].match(line):
            self.tests[self.current_test]["finished"] = self._finished(
                self.current_test, "ERROR"
            )
        if TEST_REGEX["skipped"].match(line):
            self.tests[self.current_test]["finished"] = self._finished(
                self.current_test, "SKIPPED"
            )

    def execute(self):
        """Execute a test case."""
        self.logger.info("Figure out test directory.")
        test_directory = self.test_directory(self.checkout_command)
        line = False
        self.logger.info("Change directory to test directory '%s'.", test_directory)
        with self.etos.utils.chdir(test_directory):
            self.report_path = os.path.join(test_directory, self.report_path)
            self.logger.info("Report path: %s", self.report_path)
            self.logger.info("Executing pre-execution script.")
            self._pre_execution(self._build_environment_command())
            self.logger.info("Build test command")
            command = self._build_test_command()
            self.logger.info("Run test command: %s", command)
            iterator = self.etos.utils.iterable_call(
                [command], shell=True, executable="/bin/bash", output=self.report_path
            )
            self.logger.info("Start test.")
            for _, line in iterator:
                if TEST_REGEX:
                    self.parse(line)
            self.logger.info("Finished.")
            self.result = line
