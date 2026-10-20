#!/usr/bin/env python3
"""Create the site-video environment: $SITE_VIDEO_HOME/venv (default ~/.site-video/venv). Idempotent.
Usage: scripts/sv setup [--force]"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get('SITE_VIDEO_HOME') or Path.home() / '.site-video')
VENV = HOME / 'venv'
VPY = VENV / 'bin' / 'python'
REQ = HERE / 'requirements.txt'
STATE = HOME / 'setup.json'


def fail(step, msg):
    print(f'setup FAILED at step "{step}": {msg}')
    sys.exit(1)


def run(step, cmd):
    r = subprocess.run(cmd)
    if r.returncode != 0:
        fail(step, f'command exited {r.returncode}: {" ".join(str(c) for c in cmd)}')


def main():
    force = '--force' in sys.argv[1:]
    v = sys.version_info
    if not ((3, 9) <= (v.major, v.minor) <= (3, 13)):
        fail('python', f'running Python {v.major}.{v.minor}; need 3.9 to 3.13. '
             'Fix: install Python 3.12 (e.g. brew install python@3.12) and run: python3.12 scripts/setup.py')
    HOME.mkdir(parents=True, exist_ok=True)
    if not VPY.exists():
        print(f'creating environment: {VENV}')
        run('venv', [sys.executable, '-m', 'venv', str(VENV)])
    else:
        print(f'environment exists: {VENV}')
    sha = hashlib.sha256(REQ.read_bytes()).hexdigest()
    recorded = None
    try:
        recorded = json.loads(STATE.read_text()).get('requirements_sha256')
    except Exception:
        pass
    if recorded == sha and not force:
        print('packages: requirements unchanged, pip step skipped (use --force to reinstall)')
    else:
        print('installing packages from requirements.txt')
        run('pip install', [str(VPY), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(REQ)])
    print('browser: installing Chromium (may download the browser, roughly 150 to 550 MB, only the first time)')
    run('playwright install chromium', [str(VPY), '-m', 'playwright', 'install', 'chromium'])
    STATE.write_text(json.dumps({
        'python': f'{v.major}.{v.minor}.{v.micro}',
        'requirements_sha256': sha,
        'date': datetime.date.today().isoformat(),
    }, indent=2) + '\n')
    print('setup: done')


if __name__ == '__main__':
    main()
