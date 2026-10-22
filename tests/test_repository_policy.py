"""用反例确认公开边界检查真的拒绝敏感文件。"""
import unittest
from scripts.validate_repository import file_errors


class RepositoryPolicyTests(unittest.TestCase):
    def test_reject_research_inputs_even_if_force_added(self):
        for name in ['backend/models/fish.pt', 'data/video.mp4', '.env', '.local/context.json']:
            with self.subTest(name=name):
                self.assertTrue(file_errors(name, b'example'))

    def test_reject_private_key(self):
        self.assertTrue(file_errors('key.txt', b'-----BEGIN ' + b'PRIVATE KEY-----'))

    def test_allow_fictional_fixture(self):
        self.assertEqual(file_errors('fixtures/mvp/example.json', b'{"metric": null}'), [])
