#!/usr/bin/env python3
"""Assert that every string tracks FEW_PLAYS, and that the guard stops the rest.

Written to fail rather than to print. The earlier version of this probe printed
four blocks for me to compare by eye and reported the same numbers four times,
because it reused one module name and Python served the first run's __pycache__
back for the other three. Every run here gets its own directory and its own
module name, bytecode is off, and every expectation is an assert -- a silent
pass is the only way this can succeed.
"""
import os
import shutil
import subprocess
import sys
import tempfile

SRC = os.environ.get("PL_SRC") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "possumlogic.py")
ORIG = open(SRC).read()
NEEDLE = "\nFEW_PLAYS = 2\n"
assert ORIG.count(NEEDLE) == 1, "FEW_PLAYS = 2 not found exactly once in " + SRC

PROBE = (
    "import sys, json; sys.path.insert(0, '.'); import {mod} as P;"
    "print(json.dumps({{"
    "'title': P.FEW_TITLE, 'times': P.FEW_TIMES,"
    "'anchor': P.ROTATION_SECTIONS[2][0],"
    "'heading': P.ROTATION_SECTIONS[2][1],"
    "'words': [P.rotation_word(n) for n in (0, 1, 2, 3, 4, 5, 8)]}}))"
)


def run(val):
    """Import possumlogic with FEW_PLAYS = val. Returns dict, or None if it
    refused to import at all."""
    work = tempfile.mkdtemp(prefix="few%d_" % val)
    try:
        mod = "pl_few_%d" % val
        with open(os.path.join(work, mod + ".py"), "w") as fh:
            fh.write(ORIG.replace(NEEDLE, "\nFEW_PLAYS = %d\n" % val, 1))
        r = subprocess.run(
            [sys.executable, "-B", "-c", PROBE.format(mod=mod)],
            capture_output=True, text=True, cwd=work)
        if r.returncode != 0:
            assert "FEW_NAMES only spells" in r.stderr, (
                "FEW_PLAYS=%d failed for an unexpected reason:\n%s"
                % (val, r.stderr[-1500:]))
            return None
        import json
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(work, ignore_errors=True)


EXPECT = {
    1: dict(title="Once", times="once",
            words=["", "one-off", "rarity", "rarity", "rarity", "rarity",
                   "dormant"]),
    2: dict(title="Once or twice", times="once or twice",
            words=["", "one-off", "played twice", "rarity", "rarity", "rarity",
                   "dormant"]),
    3: dict(title="Once, twice or three times",
            times="once, twice or three times",
            words=["", "one-off", "played twice", "played three times",
                   "rarity", "rarity", "dormant"]),
    4: dict(title="Once, twice, three times or four times",
            times="once, twice, three times or four times",
            words=["", "one-off", "played twice", "played three times",
                   "played four times", "rarity", "dormant"]),
}

failures = []
for val, want in sorted(EXPECT.items()):
    got = run(val)
    if got is None:
        failures.append("FEW_PLAYS=%d refused to import; it should work" % val)
        continue
    for field in ("title", "times", "words"):
        if got[field] != want[field]:
            failures.append("FEW_PLAYS=%d: %s is %r, expected %r"
                            % (val, field, got[field], want[field]))
    if got["heading"] != got["title"]:
        failures.append("FEW_PLAYS=%d: section heading %r != FEW_TITLE %r"
                        % (val, got["heading"], got["title"]))
    # No lexicon this site does not otherwise use about a show.
    for field in ("title", "times", "heading"):
        assert "night" not in got[field].lower(), (
            "FEW_PLAYS=%d: %r reintroduces the 'nights' lexicon" % (val, field))

# The value the table cannot spell must stop the build, not ship prose.
for val in (5, 9):
    if run(val) is not None:
        failures.append("FEW_PLAYS=%d imported; the guard should have raised"
                        % val)

if failures:
    print("FAIL")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("ok: 1-4 carry every derived string; 5 and 9 stop the build")
