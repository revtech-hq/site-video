"""answers test: a failing gate answered in the owner's words or with the maker's reason makes the verdict PASS; an
answer that matches two lines answers neither; an answer scoped to the other check is not read; a WARN takes an answer
too. The send gate trusts this verdict, so a loophole here ships a film. Run: scripts/sv test answers"""
import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import film_check  # noqa: E402

OWNER = {'gate': 'hold: the card', 'by': 'owner', 'words': 'hold it a little shorter', 'date': '1 Jan 2026, 10:00'}


def verdict(answers, check, lines):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        g = film_check.Gates('t', answers, check)
        for kind, name in lines:
            g.warn(name, 'm') if kind == 'warn' else g.add(name, kind == 'pass', 'm')
        ok = g.verdict()
    return ok, out.getvalue()


cases = [
    ('an owner answer passes the film', [OWNER], 'file', [('fail', 'hold: the card')], True, 'ANSW'),
    ('an unanswered failure fails it', [], 'file', [('fail', 'hold: the card')], False, 'FAIL'),
    ('an owner answer needs a date', [dict(OWNER, date='')], 'file', [('fail', 'hold: the card')], False, 'INVALID'),
    ('a maker answer needs a why', [{'gate': 'hold', 'by': 'maker'}], 'file', [('fail', 'hold: the card')], False, 'INVALID'),
    ('one answer over two failures answers neither', [dict(OWNER, gate='hold')], 'file',
     [('fail', 'hold: the card'), ('fail', 'hold: the end')], False, 'AMBIGUOUS'),
    ('an answer for the plan is not read by the file check', [dict(OWNER, check='plan')], 'file',
     [('fail', 'hold: the card')], False, 'FAIL'),
    ('an answer on a WARN is printed and counted', [dict(OWNER, gate='fast camera move')], 'plan',
     [('pass', 'blur'), ('warn', 'fast camera move 7.42-8.67 s')], True, '1 WARN answered'),
    ('an answer that matches nothing is reported', [OWNER], 'file', [('pass', 'hold: the card')], True, 'UNUSED'),
]
bad = 0
for name, answers, check, lines, want_ok, want_text in cases:
    ok, text = verdict(answers, check, lines)
    good = ok == want_ok and want_text in text
    bad += not good
    print(f"{'PASS' if good else 'FAIL'} {name}: verdict {'PASS' if ok else 'FAIL'}, prints {want_text!r}: {want_text in text}")
print('answers: OK' if not bad else f'answers: {bad} FAILED')
sys.exit(1 if bad else 0)
