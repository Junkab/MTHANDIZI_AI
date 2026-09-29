"""
Tests for the language pack lint tool.

Includes regression tests for the two real issues the linter caught the first time
it was run against chichewa_pack.json (see BUILD_LOG.md, Phase 1): a false positive
on the intentional brand-name exemption, and confirmation that strict mode correctly
blocks release while unreviewed content exists.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tool"))
from lint_pack import lint  # noqa: E402


def test_clean_entry_passes():
    pack = {"greeting": {"chi": "Moni", "en": "Hello", "audio": "x.wav", "reviewed": True}}
    assert lint(pack, strict=False) == []
    assert lint(pack, strict=True) == []


def test_missing_chi_is_caught():
    pack = {"greeting": {"en": "Hello"}}
    problems = lint(pack, strict=False)
    assert any("MISSING_CHI" in p for p in problems)


def test_empty_chi_is_caught():
    pack = {"greeting": {"chi": "   ", "en": "Hello"}}
    problems = lint(pack, strict=False)
    assert any("EMPTY_CHI" in p for p in problems)


def test_identical_to_english_is_caught():
    pack = {"greeting": {"chi": "Hello", "en": "Hello"}}
    problems = lint(pack, strict=False)
    assert any("IDENTICAL_TO_EN" in p for p in problems)


def test_identical_brand_name_is_exempt():
    """Regression: 'Mthandizi' == 'Mthandizi' is correct, not a translation gap."""
    pack = {"app_name": {"chi": "Mthandizi", "en": "Mthandizi", "exempt_identical": True}}
    problems = lint(pack, strict=False)
    assert not any("IDENTICAL_TO_EN" in p for p in problems)


def test_mismatched_placeholders_are_caught():
    pack = {"x": {"chi": "Nambala yanu ndi {reference}", "en": "Your number is {other}"}}
    problems = lint(pack, strict=False)
    assert any("BAD_PLACEHOLDER" in p for p in problems)


def test_matching_placeholders_pass():
    pack = {"x": {"chi": "Nambala yanu ndi {reference}", "en": "Your number is {reference}"}}
    problems = lint(pack, strict=False)
    assert not any("BAD_PLACEHOLDER" in p for p in problems)


def test_null_audio_without_note_is_caught():
    pack = {"x": {"chi": "test", "en": "test2", "audio": None}}
    problems = lint(pack, strict=False)
    assert any("NO_AUDIO_NO_NOTE" in p for p in problems)


def test_null_audio_with_note_passes():
    pack = {"x": {"chi": "test", "en": "test2", "audio": None, "note": "dynamic"}}
    problems = lint(pack, strict=False)
    assert not any("NO_AUDIO_NO_NOTE" in p for p in problems)


def test_dev_mode_ignores_unreviewed():
    pack = {"x": {"chi": "test", "en": "test2", "reviewed": False}}
    assert lint(pack, strict=False) == []


def test_strict_mode_requires_reviewed():
    """The release-blocking behaviour: nothing ships until a human approves it."""
    pack = {"x": {"chi": "test", "en": "test2", "reviewed": False}}
    problems = lint(pack, strict=True)
    assert any("UNREVIEWED" in p for p in problems)


def test_strict_mode_passes_when_reviewed():
    pack = {"x": {"chi": "test", "en": "test2", "reviewed": True}}
    assert lint(pack, strict=True) == []


def test_nested_structure_is_walked():
    pack = {
        "speech": {"greeting": {"chi": "Moni", "en": "Hello", "reviewed": True}},
        "ui": {"button": {"chi": "Inde", "en": "Yes", "reviewed": True}},
    }
    assert lint(pack, strict=True) == []


def test_real_pack_file_is_structurally_clean():
    """The actual chichewa_pack.json shipped in this repo must pass dev-mode lint."""
    pack_path = Path(__file__).parent.parent / "pack" / "chichewa_pack.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    problems = lint(pack, strict=False)
    assert problems == [], f"chichewa_pack.json has structural issues: {problems}"


def test_real_pack_file_is_not_yet_release_ready():
    """
    Documents current state: strict mode SHOULD fail right now, because no native
    speaker has reviewed the pack yet. If this test ever fails, it means the pack
    somehow got marked fully reviewed without that actually happening - investigate,
    don't just delete the test.
    """
    pack_path = Path(__file__).parent.parent / "pack" / "chichewa_pack.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    problems = lint(pack, strict=True)
    assert any("UNREVIEWED" in p for p in problems)
