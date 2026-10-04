"""
Tests for the provenance contract.

Run: python3 -m pytest tests/ -q      (from the repo root)

These assert the two things that actually matter: that a state cannot reach
data/sites.json without complete provenance, and that a frozen state's unknown
extraction date stays null rather than being filled with a plausible guess.

Each test is written so it CAN fail. test_guard_can_fail and
test_live_entry_rejects_a_guessed_null below exist specifically to prove the
validator is not vacuously returning an empty problem list.
"""
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))

import provenance as P  # noqa: E402  (needs the sys.path line above)


def _complete_live():
    return {
        'status': 'live',
        'source_repo': 'peyton1754/WestVirginiaDCScreener',
        'source_commit': '7d9bab6fa0ab3ab6a87142af90bccdc863dd6a31',
        # as_of is the upstream DATA's date; extracted_on is the copy date.
        # They differ here on purpose: that gap is the thing being tracked.
        'as_of': '2026-07-16',
        'extracted_on': '2026-10-04',
        'pipeline_run': 'local run 2026-10-04',
        'sites': 22,
    }


def _complete_frozen():
    return {
        'status': 'frozen',
        'source_repo': 'Arthurfok1/TennesseeDCScreener',
        'as_of': None,
        'extracted_on_or_before': '2026-07-22',
        'sites': 36,
        'note': 'Upstream unreachable; bound from this repo git history.',
    }


# --- the positive controls: a correct entry must pass ----------------------
# If either of these ever fails, the validator has become too strict and every
# "no problems" result below is meaningless.

def test_complete_live_entry_passes():
    assert P.validate_entry('WV', _complete_live()) == []


def test_complete_frozen_entry_passes():
    assert P.validate_entry('TN', _complete_frozen()) == []


# --- the guard must reject what it exists to reject ------------------------

@pytest.mark.parametrize('missing', P.LIVE_REQUIRED)
def test_live_entry_missing_any_required_key_is_rejected(missing):
    entry = _complete_live()
    del entry[missing]
    problems = P.validate_entry('WV', entry)
    assert problems, f"removing {missing!r} from a live entry was not caught"


@pytest.mark.parametrize('key', ('source_commit', 'as_of', 'extracted_on', 'source_repo'))
def test_live_entry_rejects_a_guessed_null(key):
    """A live state with an empty commit or date is the hole this module closes.

    An explicit null has to be rejected as firmly as a missing key, or the
    contract can be satisfied by writing the keys and leaving them blank.
    """
    entry = _complete_live()
    entry[key] = None
    problems = P.validate_entry('WV', entry)
    assert any(key in p for p in problems), \
        f"a live entry with {key}=None passed validation"


def test_frozen_entry_with_a_filled_as_of_is_rejected():
    """The whole point of frozen: the date is unknown and must stay unknown.

    Filling it with today, a file mtime or a plausible-looking date turns a
    stated gap into a false fact, which is worse than the gap.
    """
    entry = _complete_frozen()
    entry['as_of'] = '2026-07-22'  # the bound, misused as the actual date
    problems = P.validate_entry('TN', entry)
    assert any('as_of' in p for p in problems), \
        "a frozen entry with a filled as_of passed validation"


def test_as_of_is_the_data_date_not_the_copy_date():
    """Regression guard for the flaw this contract was built with and then fixed.

    The first draft used today's date as as_of, so re-running the extractor
    against an unchanged upstream reset the clock and made months-old screening
    data read as fresh. The shipped WV entry must keep the two apart: its data
    is from July and its copy is from October, and a banner that reported the
    copy date would be worse than no banner.
    """
    with open(os.path.join(REPO_ROOT, 'data', 'provenance.json')) as f:
        prov = json.load(f)
    wv = prov['WV']
    assert wv['as_of'] < wv['extracted_on'], (
        f"WV as_of {wv['as_of']} is not older than extracted_on "
        f"{wv['extracted_on']}; as_of may have been set to the copy date")


def test_frozen_entry_without_a_bound_is_rejected():
    entry = _complete_frozen()
    del entry['extracted_on_or_before']
    assert P.validate_entry('TN', entry), "frozen entry with no bound passed"


def test_unknown_status_is_rejected():
    entry = _complete_live()
    entry['status'] = 'probably-fine'
    assert P.validate_entry('WV', entry), "an invented status passed validation"


def test_state_with_no_entry_at_all_is_rejected():
    problems = P.validate({'WV': _complete_live()}, ['WV', 'OH'])
    assert any(p.startswith('OH') for p in problems)
    assert not any(p.startswith('WV') for p in problems)


def test_guard_can_fail():
    """Mutation control: a validator that always returns [] must not pass.

    Without this, every "problems is non-empty" assertion above could be
    satisfied by a validator that is merely broken in the other direction, and
    every "== []" assertion by one that always returns []. This asserts the two
    directions are actually distinguishable on the same input shape.
    """
    good = P.validate_entry('WV', _complete_live())
    bad = P.validate_entry('WV', {'status': 'live'})
    assert good == [] and bad != [], \
        "validator does not distinguish a complete entry from an empty one"


# --- the shipped file itself ----------------------------------------------

def test_shipped_provenance_covers_every_state_in_sites_json():
    """Every state with rows on the map has an entry, and vice versa."""
    with open(os.path.join(REPO_ROOT, 'data', 'sites.json')) as f:
        sites = json.load(f)
    with open(os.path.join(REPO_ROOT, 'data', 'provenance.json')) as f:
        prov = json.load(f)
    states_in_data = {s['state'] for s in sites}
    assert states_in_data == set(prov), (
        f"states in sites.json {sorted(states_in_data)} do not match "
        f"provenance.json {sorted(prov)}")


def test_shipped_provenance_is_valid():
    with open(os.path.join(REPO_ROOT, 'data', 'provenance.json')) as f:
        prov = json.load(f)
    assert P.validate(prov, sorted(prov)) == []


def test_shipped_provenance_counts_match_the_data():
    with open(os.path.join(REPO_ROOT, 'data', 'sites.json')) as f:
        sites = json.load(f)
    with open(os.path.join(REPO_ROOT, 'data', 'provenance.json')) as f:
        prov = json.load(f)
    actual = {}
    for s in sites:
        actual[s['state']] = actual.get(s['state'], 0) + 1
    for st, entry in prov.items():
        assert entry['sites'] == actual.get(st), (
            f"{st}: provenance says {entry['sites']}, sites.json has "
            f"{actual.get(st)}")


# --- the guard end to end -------------------------------------------------

def test_merge_sites_refuses_a_state_with_no_provenance(tmp_path):
    """merge_sites.py must exit non-zero and write nothing for an unknown state.

    Uses a real subprocess against the real script so the test exercises the
    actual entry point, not a re-implementation of it.
    """
    before = open(os.path.join(REPO_ROOT, 'data', 'sites.json'), 'rb').read()
    out = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, 'scripts', 'merge_sites.py'), 'oh'],
        capture_output=True, text=True, cwd=REPO_ROOT)
    after = open(os.path.join(REPO_ROOT, 'data', 'sites.json'), 'rb').read()
    assert out.returncode != 0, f"merge_sites.py accepted an unprovenanced state:\n{out.stdout}"
    assert 'provenance' in (out.stderr + out.stdout).lower()
    assert before == after, "data/sites.json changed on a refused merge"
