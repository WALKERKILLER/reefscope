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


class LearningDistributionTests(unittest.TestCase):
    def setUp(self):
        import shutil
        import tempfile
        from pathlib import Path
        from scripts.validate_repository import ROOT

        self.sandbox = tempfile.TemporaryDirectory(prefix='.tmp-guidance-', dir=ROOT)
        self.addCleanup(self.sandbox.cleanup)
        self.root = Path(self.sandbox.name)
        for name in ['AGENTS.md', 'CLAUDE.md', '.gitignore', '.repo-seed/upstream.json']:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        shutil.copytree(ROOT / '.agents/skills/vibe-wise-learn', self.root / '.agents/skills/vibe-wise-learn')

    def test_complete_distribution_passes_integrity_check(self):
        from scripts.validate_repository import validate_learning_contract
        self.assertEqual(validate_learning_contract(self.root), [])

    def test_missing_or_modified_behavior_is_rejected(self):
        from scripts.validate_repository import validate_learning_contract
        guide = self.root / '.agents/skills/vibe-wise-learn/behavior.md'
        guide.write_text('Changed checkpoint behavior')
        self.assertTrue(validate_learning_contract(self.root))
        guide.unlink()
        self.assertTrue(validate_learning_contract(self.root))

    def test_missing_agent_route_is_rejected(self):
        from scripts.validate_repository import validate_learning_contract
        (self.root / 'AGENTS.md').write_text('# No skill route')
        self.assertTrue(validate_learning_contract(self.root))

    def test_legacy_learning_state_is_private(self):
        from scripts.validate_repository import validate_learning_contract
        self.assertTrue(file_errors('.sensible-vibes/profile.md', b'learner state'))
        ignore = self.root / '.gitignore'
        ignore.write_text(ignore.read_text().replace('.sensible-vibes/', ''))
        self.assertTrue(validate_learning_contract(self.root))
