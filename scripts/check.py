"""本地与 CI 共用的门禁入口。"""
from pathlib import Path
import subprocess
import sys


def main():
    if not __debug__:
        raise SystemExit('检查包含 assert，禁止用 python -O 执行。')
    root = Path(__file__).resolve().parents[1]
    # 治理校验器由上游 manifest 选择；以下只编排项目专属证据。
    gates = [
        ['node', 'scripts/run-gates.mjs'],
        ['python3', 'scripts/validate_repository.py'],
        ['python3', 'docs/mvp/validate_fixtures.py'],
        ['python3', '-m', 'unittest', 'discover', '-s', 'tests'],
        ['git', 'diff', '--check'],
        ['git', 'diff', '--cached', '--check'],
    ]
    for gate in gates:
        command = [sys.executable if item == 'python3' else item for item in gate]
        print('+ ' + ' '.join(gate), flush=True)
        subprocess.run(command, cwd=root, check=True)


if __name__ == '__main__':
    main()
