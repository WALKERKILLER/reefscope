"""项目专属检查：公开文件边界、Agent 入口与学习分发；治理链接由上游 gate 负责。"""
import json
import hashlib
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'README.md', 'AGENTS.md', 'CONTRIBUTING.md', 'docs/README.md',
    'docs/developers/README.md', 'docs/agents/README.md',
    'docs/agents/workflow.md', 'docs/agents/project-map.md',
    'docs/agents/runtime-requirements.md', 'docs/agents/disclosure-policy.md',
    'docs/agents/runtime-playbook.md', 'docs/agents/failure-index.md',
    'docs/agents/execution-log.md', 'docs/agents/memory.json',
    '.github/workflows/ci.yml', '.github/workflows/publish.yml',
    '.repo-seed/manifest.json', '.repo-seed/upstream.json', 'CLAUDE.md',
    '.agents/skills/repo-review/SKILL.md', '.agents/skills/repo-decisions/SKILL.md',
    '.agents/skills/repo-governance/SKILL.md',
]
BLOCKED_SUFFIXES = {'.pt', '.pth', '.onnx', '.safetensors', '.mp4', '.mov', '.avi', '.zip', '.sqlite3', '.log'}
SECRET = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')


def file_errors(path, data):
    errors = []
    parts = Path(path).parts
    if any(p in {'.local', '.vibe-wise', '.sensible-vibes', 'node_modules', '.venv'} for p in parts):
        errors.append(f'{path}: private/generated directory')
    if Path(path).suffix.lower() in BLOCKED_SUFFIXES or (Path(path).name.startswith('.env') and Path(path).name != '.env.example'):
        errors.append(f'{path}: forbidden research input or secret file')
    if len(data) > 2_000_000:
        errors.append(f'{path}: exceeds 2 MB; use artifact storage')
    if SECRET.search(data.decode('utf-8', errors='ignore')):
        errors.append(f'{path}: suspected credential; inspect locally')
    return errors


def validate_learning_contract(root=ROOT):
    """证明可随克隆分发的学习入口/内容完整，不声称验证了 LLM 对话质量。"""
    errors = []
    source = json.loads((root / '.repo-seed/upstream.json').read_text())['vibe_wise']
    expected = {'SKILL.md', 'behavior.md', 'codex.md', 'onboarding.md', 'state-templates.md', 'agents/openai.yaml'}
    directory = '.agents/skills/vibe-wise-learn/'
    paths = {item['path'] for item in source['files']}
    if paths != {directory + name for name in expected}:
        errors.append('VibeWise: incomplete or unexpected guide inventory')
    for item in source['files']:
        path = root / item['path']
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            errors.append('VibeWise: missing/unsafe guide ' + item['path'])
        elif hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            errors.append('VibeWise: guide digest drift ' + item['path'])
    agents = (root / 'AGENTS.md').read_text()
    if directory + 'SKILL.md' not in agents or 'learning-workflow.md' not in agents:
        errors.append('VibeWise: root agent route missing')
    if '@AGENTS.md' not in (root / 'CLAUDE.md').read_text().splitlines():
        errors.append('VibeWise: CLAUDE must import the same AGENTS rules')
    ignore = (root / '.gitignore').read_text().splitlines()
    for entry in ['.vibe-wise/', '.sensible-vibes/']:
        if entry not in ignore:
            errors.append('VibeWise: local learner state must be ignored: ' + entry)
    if not (root / source['license']).is_file():
        errors.append('VibeWise: MIT notice missing')
    return errors


def validate(root=ROOT):
    errors = [f'missing: {p}' for p in REQUIRED if not (root / p).is_file()]
    manifest = json.loads((root / '.repo-seed/manifest.json').read_text())
    for owner in manifest['governance']['paths'].values():
        if not (root / owner).exists():
            errors.append(f'missing owner: {owner}')
    errors.extend(validate_learning_contract(root))
    # 检查 Git 可见文件，忽略本地副本、依赖与敏感输入。
    names = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=root).decode().split('\0')
    for name in sorted(set(names) - {''}):
        path = root / name
        if path.is_symlink():
            errors.append(f'{name}: symlink requires explicit review')
            continue
        if not path.is_file():
            continue
        data = path.read_bytes()
        errors.extend(file_errors(name, data))
    return errors


if __name__ == '__main__':
    failures = validate()
    if failures:
        raise SystemExit('\n'.join(failures))
    print('PASS: project structure, tracked-file boundaries and learning distribution')
