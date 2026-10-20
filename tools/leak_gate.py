#!/usr/bin/env python3
"""Leak gate: scans content for names, personal paths, dated quotes and em dashes.
  python3 tools/leak_gate.py --staged        scan the staged content of every staged file (default)
  python3 tools/leak_gate.py PATH...         scan files or folders on disk
  python3 tools/leak_gate.py --no-names ...  run every rule but the names (said in the output)
  python3 tools/leak_gate.py --self-test     prove every rule catches its planted case
The names live outside this repository, in a private list: the file named by $LEAK_GATE_NAMES, else by
`git config leakgate.names`. One entry per line, matched as a whole word in any letter case; "case:" before an entry
matches that case only; lines starting with # are comments. Without a list the gate refuses to run (exit 2).
Allowlist: tools/leak-allow.txt, lines of `<path>:<exact substring>`."""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOW = os.path.join(HERE, 'leak-allow.txt')

PATHS = ['/Users/', '/home/', '/private/tmp', '/private/var', '~/Claude', '/Volumes/', 'C:\\', '/System/Library']
MONTH = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
DATE_RE = re.compile(r'\b\d{1,2}\s+' + MONTH + r'\b(?:\s+\d{4})?|\b' + MONTH + r'\s+\d{1,2}(?:,\s*\d{4})?\b|\b\d{4}-\d{2}-\d{2}\b')
QUOTE_RE = re.compile('["\u201c\u201d]')
EMDASH = '\u2014'
NAME_RES = None          # set by use_names(); None means the names rule is off


def names_file():
    p = os.environ.get('LEAK_GATE_NAMES')
    if not p:
        r = subprocess.run(['git', '-C', HERE, 'config', '--get', 'leakgate.names'], capture_output=True, text=True)
        p = r.stdout.strip()
    return p or None


def use_names(path):
    """the names rule from the private list: one regex for the entries in any case, one for the case: entries"""
    global NAME_RES
    ci, cs = [], []
    for raw in open(path, encoding='utf-8'):
        e = raw.strip()
        if not e or e.startswith('#'):
            continue
        (cs if e.startswith('case:') else ci).append(e[5:] if e.startswith('case:') else e)
    word = lambda xs: r'(?<![\w.-])(' + '|'.join(re.escape(x) for x in xs) + r')(?![\w])'
    NAME_RES = [re.compile(word(xs), f) for xs, f in ((ci, re.I), (cs, 0)) if xs]
    return len(ci) + len(cs)


def scan_text(path, text):
    found = []
    for i, line in enumerate(text.splitlines(), 1):
        rules = []
        if NAME_RES and any(r.search(line) for r in NAME_RES):
            rules.append('name')
        if any(p in line for p in PATHS):
            rules.append('path')
        if DATE_RE.search(line) and QUOTE_RE.search(line):
            rules.append('dated-quote')
        if EMDASH in line:
            rules.append('em-dash')
        for r in dict.fromkeys(rules):
            found.append((path, i, r, line.strip()[:80], line))
    return found


def load_allow():
    out = []
    if os.path.exists(ALLOW):
        for raw in open(ALLOW, encoding='utf-8'):
            raw = raw.rstrip('\n')
            if not raw.strip() or raw.lstrip().startswith('#') or ':' not in raw:
                continue
            p, s = raw.split(':', 1)
            out.append((p.strip(), s))
    return out


def allowed(finding, allow):
    return any(os.path.normpath(finding[0]) == os.path.normpath(p) and s in finding[4] for p, s in allow)


def is_binary(data):
    return b'\0' in data[:8192]


def files_on_disk(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = [d for d in dirs if d != '.git']
                for n in sorted(names):
                    yield os.path.join(root, n)
        else:
            yield p


def staged_files():
    top = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
    names = subprocess.check_output(['git', '-C', top, 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'])
    for n in names.decode('utf-8').split('\0'):
        if n:
            data = subprocess.check_output(['git', '-C', top, 'show', ':' + n])
            yield n, data


def run(items):
    allow = load_allow()
    findings, k = [], 0
    for path, data in items:
        if is_binary(data):
            continue
        k += 1
        for f in scan_text(path, data.decode('utf-8', 'replace')):
            if not allowed(f, allow):
                findings.append(f)
    return findings, k


def report(findings, k):
    for p, i, r, ex, _ in findings:
        print(f'{p}:{i}: {r}: {ex}')
    off = '' if NAME_RES is not None else ' (names rule OFF: --no-names)'
    if findings:
        print(f'leak gate: {len(findings)} findings{off}')
        return 1
    print(f'leak gate: clean ({k} files){off}')
    return 0


def self_test():
    fails = []
    with tempfile.TemporaryDirectory() as d:
        lst = os.path.join(d, 'names.txt')
        open(lst, 'w', encoding='utf-8').write('# planted names\nzorblax\nquux corp\ncase:WIDGET-PLAN\n')
        use_names(lst)
        cases = {
            'name': 'Made for Zorblax last week, and for Quux Corp',
            'path': 'open ' + PATHS[0] + 'someone/file.txt',
            'dated-quote': 'He said \u201cship it\u201d on ' + '15 Oct ' + '2026',
            'em-dash': 'one ' + EMDASH + ' two',
        }
        for rule, line in cases.items():
            if rule not in [f[2] for f in scan_text('x', line)]:
                fails.append(f'rule {rule} did not catch: {line}')
        if scan_text('x', 'A plain line about a film and its frames.'):
            fails.append('clean line was flagged')
        if not any(f[2] == 'name' for f in scan_text('x', 'see WIDGET-PLAN.md')):
            fails.append('a case: entry was not caught in its own case')
        if any(f[2] == 'name' for f in scan_text('x', 'see widget-plan.md')):
            fails.append('a case: entry was caught in another case')
        if any(f[2] == 'name' for f in scan_text('x', 'a zorblaxmore and a quuxcorp look')):
            fails.append('whole-word match broken')
        env = dict(os.environ, LEAK_GATE_NAMES=os.path.join(d, 'missing.txt'))
        r = subprocess.run([sys.executable, os.path.abspath(__file__), os.path.join(d, 'names.txt')], env=env,
                           capture_output=True, text=True)
        if r.returncode != 2:
            fails.append(f'a missing names list did not refuse to run (exit {r.returncode})')
    if fails:
        print('self-test: FAIL')
        for f in fails:
            print('  ' + f)
        return 1
    print('self-test: PASS')
    return 0


def main():
    args = sys.argv[1:]
    if args == ['--self-test']:
        sys.exit(self_test())
    no_names = '--no-names' in args
    args = [a for a in args if a != '--no-names']
    if not no_names:
        p = names_file()
        if not p or not os.path.isfile(p):
            print('leak gate: no names list (' + (p or 'not configured') + '). Point the gate at the private list: '
                  'git config leakgate.names FILE (or LEAK_GATE_NAMES=FILE); --no-names skips the rule on purpose.')
            sys.exit(2)
        use_names(p)
    if not args or args == ['--staged']:
        items = list(staged_files())
    else:
        items = []
        for p in files_on_disk(args):
            try:
                items.append((p, open(p, 'rb').read()))
            except OSError as e:
                print(f'cannot read {p}: {e}')
    sys.exit(report(*run(items)))


if __name__ == '__main__':
    main()
