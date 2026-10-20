#!/usr/bin/env python3
"""Check the machine and the site-video environment. Usage: scripts/sv doctor"""
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SV = HERE / 'sv'
HOME = Path(os.environ.get('SITE_VIDEO_HOME') or Path.home() / '.site-video')
VPY = HOME / 'venv' / 'bin' / 'python'
REQ = HERE / 'requirements.txt'

results = []


def report(name, ok, detail, fix=None):
    results.append(ok)
    print(f'{"PASS" if ok else "FAIL"} {name}: {detail}')
    if not ok and fix:
        print(f'  fix: {fix}')


def pins():
    out = {}
    for line in REQ.read_text().splitlines():
        m = re.match(r'^\s*([A-Za-z0-9_.\-]+)==(\S+)', line)
        if m:
            out[m.group(1).lower().replace('_', '-')] = m.group(2)
    return out


def check_tools():
    if platform.system() != 'Darwin':
        return report('tools', True, 'not macOS, skipped')
    try:
        r = subprocess.run(['xcode-select', '-p'], capture_output=True, text=True, timeout=20)
        ok, d = r.returncode == 0, (r.stdout.strip() or 'Command Line Tools not installed')
    except Exception as e:
        ok, d = False, f'xcode-select failed: {e}'
    report('tools', ok, d, 'xcode-select --install')


def check_python():
    v = sys.version_info
    ok = (3, 9) <= (v.major, v.minor) <= (3, 13)
    report('python', ok, f'{v.major}.{v.minor}.{v.micro}' + ('' if ok else ' (need 3.9 to 3.13)'),
           'install Python 3.12 (e.g. brew install python@3.12)')


def check_env():
    report('environment', VPY.exists(), str(VPY) if VPY.exists() else f'missing {VPY}', f'{SV} setup')
    return VPY.exists()


def check_packages():
    code = ('import PIL, importlib.metadata as m; print(PIL.__version__); print(m.version("playwright"))')
    try:
        r = subprocess.run([str(VPY), '-c', code], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return report('packages', False, 'import failed: ' + r.stderr.strip().splitlines()[-1], f'{SV} setup --force')
        got = r.stdout.split()
    except Exception as e:
        return report('packages', False, str(e), f'{SV} setup --force')
    p = pins()
    ok = got == [p.get('pillow'), p.get('playwright')]
    report('packages', ok, f'Pillow {got[0]}, playwright {got[1]}' + ('' if ok else
           f' (pins: Pillow {p.get("pillow")}, playwright {p.get("playwright")})'), f'{SV} setup --force')


def check_browser():
    code = ('from playwright.sync_api import sync_playwright\n'
            'with sync_playwright() as p:\n'
            '    b = p.chromium.launch(headless=True)\n'
            '    pg = b.new_page(); pg.goto("about:blank"); b.close()\n')
    try:
        r = subprocess.run([str(VPY), '-c', code], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return report('browser', True, 'Chromium launched headless and opened about:blank')
        err = r.stderr.strip()
    except subprocess.TimeoutExpired:
        err = 'timed out after 60 s'
    except Exception as e:
        err = str(e)
    last = (err.splitlines() or ['unknown error'])[-1][:160]
    if re.search(r'sandbox|permission|Operation not permitted', err, re.I):
        report('browser', False, f"{last} (Claude Code's sandbox may be blocking the browser)",
               'run the film commands outside the sandbox')
    else:
        report('browser', False, last, f'{SV} setup')


def check_network():
    try:
        socket.create_connection(('example.com', 443), timeout=5).close()
        report('network', True, 'example.com:443 reachable')
    except Exception as e:
        report('network', False, f'cannot reach example.com:443 ({e})',
               'check the connection or proxy; films of live pages need it')


def check_ffmpeg():
    ff, fp = shutil.which('ffmpeg'), shutil.which('ffprobe')
    brew = shutil.which('brew')
    fix = 'brew install ffmpeg' if brew else 'install Homebrew (see brew.sh), then brew install ffmpeg'
    if not (ff and fp):
        missing = ' and '.join(n for n, w in (('ffmpeg', ff), ('ffprobe', fp)) if not w)
        return report('ffmpeg', False, f'{missing} not on PATH', fix)
    try:
        out = subprocess.run([ff, '-hide_banner', '-encoders'], capture_output=True, text=True, timeout=30).stdout
    except Exception as e:
        return report('ffmpeg', False, str(e), fix)
    ok = 'libx264' in out
    report('ffmpeg', ok, f'{ff}, libx264 ' + ('present' if ok else 'missing'), fix)


def check_disk():
    free = shutil.disk_usage(os.getcwd()).free / 1e9
    report('disk', free >= 5, f'{free:.1f} GB free in {os.getcwd()}',
           'free space, or run the film from a folder on a disk with room (one film\'s capture takes about 1.5 GB)')


def main():
    check_tools()
    check_python()
    if check_env():
        check_packages()
        check_browser()
    else:
        for n in ('packages', 'browser'):
            report(n, False, 'skipped: no environment', f'{SV} setup')
    check_network()
    check_ffmpeg()
    check_disk()
    n_fail = results.count(False)
    print(f'doctor: {len(results) - n_fail} PASS, {n_fail} FAIL')
    sys.exit(1 if n_fail else 0)


if __name__ == '__main__':
    main()
