import unittest
from unittest.mock import MagicMock, patch

from telicent_lib.utils import clean_hostname, generate_group_id

from .test_data.utils_test_hosts import host_data


class TestGenerateGroupID(unittest.TestCase):

    @patch('telicent_lib.utils.os.environ', {})
    def test_clean_hostname_non_k8s(self):

        for hostname, expected in zip(host_data["hosts"], host_data["expected_hosts"]):
            result = clean_hostname(hostname)
            self.assertEqual(result, expected, f"Failed for hostname: {hostname} in non-K8s environment")

    @patch('telicent_lib.utils.os.environ', {})
    def test_clean_hostname_max_len(self):

        hostname = 'x' * 300
        result = clean_hostname(hostname)
        self.assertEqual(len(result), 200, f"Failed for hostname: {hostname} in non-K8s environment")

    @patch.dict('telicent_lib.utils.os.environ', {"KUBERNETES_SERVICE_HOST": "some_value"})
    def test_clean_hostname_k8s(self):
        for hostname, expected in zip(host_data["k8s_hosts"], host_data["k8s_expected_hosts"]):
            result = clean_hostname(hostname)
            self.assertEqual(result, expected, f"Failed for hostname: {hostname} in K8s environment")


    @patch('telicent_lib.utils.socket.gethostname')
    @patch('telicent_lib.utils.inspect.stack')
    def test_generate_group_id_with_predefined_hosts(self, mock_stack, mock_gethostname):
        mock_frame = MagicMock()
        mock_frame.filename = "test_filename"
        mock_frame.lineno = 101
        mock_stack.return_value = [None, mock_frame]

        mock_hostnames = ["host_one", "host_two", "host_three"]
        expected_group_ids = [
            "host_one_5b9a7c76c1",
            "host_two_5b9a7c76c1",
            "host_three_5b9a7c76c1"
        ]

        for mock_hostname, expected_group_id in zip(mock_hostnames, expected_group_ids):
            mock_gethostname.return_value = mock_hostname

            group_id = generate_group_id()

            self.assertEqual(group_id, expected_group_id)

    @patch('telicent_lib.utils.socket.gethostname')
    @patch('telicent_lib.utils.inspect.stack')
    def test_generate_group_id_with_predefined_hosts_should_fail(self, mock_stack, mock_gethostname):
        mock_frame = MagicMock()
        mock_frame.filename = "test_filename"
        mock_frame.lineno = 103
        mock_stack.return_value = [None, mock_frame]

        mock_hostnames = ["host_one", "host_two", "host_three"]
        expected_group_ids = [
            "host_one_5b9a7c76c1",
            "host_two_5b9a7c76c1",
            "host_three_5b9a7c76c1"
        ]

        for mock_hostname, expected_group_id in zip(mock_hostnames, expected_group_ids):
            mock_gethostname.return_value = mock_hostname

            group_id = generate_group_id()

            self.assertNotEqual(group_id, expected_group_id)

