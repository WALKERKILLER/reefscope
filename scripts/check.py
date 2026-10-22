"""本地与 CI 共用的门禁入口。"""
import json
from pathlib import Path
import subprocess
import sys


def main():
    if not __debug__:
        raise SystemExit('检查包含 assert，禁止用 python -O 执行。')
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / '.repo/governance.json').read_text())
    for gate in manifest['gates']:
        command = [sys.executable if item == 'python3' else item for item in gate]
        print('+ ' + ' '.join(gate), flush=True)
        subprocess.run(command, cwd=root, check=True)


if __name__ == '__main__':
    main()
