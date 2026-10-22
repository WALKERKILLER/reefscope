"""标准库治理检查：入口完整、相对文档链接可达、公开文件边界。"""
import json
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
]
BLOCKED_SUFFIXES = {'.pt', '.pth', '.onnx', '.safetensors', '.mp4', '.mov', '.avi', '.zip', '.sqlite3', '.log'}
SECRET = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')


def file_errors(path, data):
    errors = []
    parts = Path(path).parts
    if any(p in {'.local', '.vibe-wise', 'node_modules', '.venv'} for p in parts):
        errors.append(f'{path}: private/generated directory')
    if Path(path).suffix.lower() in BLOCKED_SUFFIXES or (Path(path).name.startswith('.env') and Path(path).name != '.env.example'):
        errors.append(f'{path}: forbidden research input or secret file')
    if len(data) > 2_000_000:
        errors.append(f'{path}: exceeds 2 MB; use artifact storage')
    if SECRET.search(data.decode('utf-8', errors='ignore')):
        errors.append(f'{path}: suspected credential; inspect locally')
    return errors


def validate(root=ROOT):
    errors = [f'missing: {p}' for p in REQUIRED if not (root / p).is_file()]
    manifest = json.loads((root / '.repo/governance.json').read_text())
    for owner in manifest['owners'].values():
        if not (root / owner).is_file():
            errors.append(f'missing owner: {owner}')
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
        if path.suffix == '.md':
            # shortcut: 只检查内联相对链接的目标文件，新增引用式链接时扩展检查。
            text = re.sub(r'```.*?```', '', data.decode('utf-8'), flags=re.S)
            for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text):
                if ':' in target or target.startswith('#'):
                    continue
                target = target.split('#')[0]
                if target and not (path.parent / target).exists():
                    errors.append(f'{name}: broken link {target}')
    return errors


if __name__ == '__main__':
    failures = validate()
    if failures:
        raise SystemExit('\n'.join(failures))
    print('PASS: repository structure, relative links and tracked-file boundaries')
