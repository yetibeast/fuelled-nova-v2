"""Role-based system prompt personalization.

Two Fuelled users get a short additive role block appended to the default
system prompt; all other emails get the default unchanged.
"""
from __future__ import annotations

from app.pricing_v2.prompts import build_system_prompt


SHREYA = "shreya.garg@fuelled.com"
SHAWN = "shawn.krienke@fuelled.com"


def test_default_prompt_unchanged_for_unknown_email():
    baseline = build_system_prompt()
    for email in (None, "", "curtis@example.com", "mark.ledain@fuelled.com"):
        assert build_system_prompt(email=email) == baseline, (
            f"Unknown email {email!r} must get the default prompt byte-for-byte"
        )


def test_shreya_block_appended():
    baseline = build_system_prompt()
    personalized = build_system_prompt(email=SHREYA)
    assert personalized.startswith(baseline), "Role block must be additive, not replacing"
    suffix = personalized[len(baseline):].lower()
    assert "shreya" in suffix
    assert "mailing" in suffix or "content" in suffix
    assert len(suffix.strip().splitlines()) <= 4, "Role block should be 2-3 short lines"


def test_shawn_block_appended():
    baseline = build_system_prompt()
    personalized = build_system_prompt(email=SHAWN)
    assert personalized.startswith(baseline), "Role block must be additive, not replacing"
    suffix = personalized[len(baseline):].lower()
    assert "shawn" in suffix
    assert "sales" in suffix or "bid" in suffix
    assert len(suffix.strip().splitlines()) <= 4, "Role block should be 2-3 short lines"


def test_email_match_is_case_insensitive():
    for variant in (SHREYA.upper(), " " + SHAWN + " "):
        personalized = build_system_prompt(email=variant)
        baseline = build_system_prompt()
        assert len(personalized) > len(baseline), (
            f"Email {variant!r} should match after normalization"
        )
