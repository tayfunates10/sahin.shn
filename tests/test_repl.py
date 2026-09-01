from __future__ import annotations

import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.repl import ReplLimitError, ReplLimits, ReplSemanticError, ReplSession


def test_repl_persists_scope_without_replaying_old_output():
    repl = ReplSession()

    first = repl.evaluate('x = 2\nyaz x\n')
    second = repl.evaluate('x = x + 3\nyaz x\n')

    assert first.output == ('2',)
    assert second.output == ('5',)
    assert second.values['x'] == 5
    assert repl.snippet_count == 2


def test_repl_rejects_semantic_error_without_committing_history():
    repl = ReplSession()

    with pytest.raises(ReplSemanticError):
        repl.evaluate('yaz bilinmeyen\n')

    assert repl.snippet_count == 0
    assert repl.history_chars == 0


def test_repl_rolls_back_runtime_state_when_evaluation_fails():
    repl = ReplSession()
    repl.evaluate('x = 1\n')

    with pytest.raises(Exception):
        repl.evaluate('x = 2\nyaz 1 / 0\n')

    result = repl.evaluate('yaz x\n')
    assert result.output == ('1',)
    assert result.values['x'] == 1
    assert repl.snippet_count == 2


def test_repl_failed_binding_does_not_leak_into_runtime_scope():
    repl = ReplSession()
    repl.evaluate('x = 1\n')

    with pytest.raises(Exception):
        repl.evaluate('geçici <- 7\nyaz 1 / 0\n')

    result = repl.evaluate('geçici = 9\nyaz geçici\n')
    assert result.output == ('9',)
    assert result.values['geçici'] == 9


def test_repl_capabilities_are_default_deny_and_copied_from_ceiling():
    repl = ReplSession()
    with pytest.raises(CapabilityError, match='SHN-G001'):
        repl.require_capability(Capability.DOSYA_OKU)

    source_caps = CapabilitySet().grant(Capability.DOSYA_OKU)
    allowed = ReplSession(capabilities=source_caps)
    source_caps.grant(Capability.AG)

    allowed.require_capability(Capability.DOSYA_OKU)
    with pytest.raises(CapabilityError):
        allowed.require_capability(Capability.AG)


def test_repl_enforces_snippet_and_history_resource_limits_fail_closed():
    repl = ReplSession(limits=ReplLimits(max_snippet_chars=8, max_history_chars=12, max_snippets=2))

    repl.evaluate('x = 1\n')
    with pytest.raises(ReplLimitError, match='SHN-R002'):
        repl.evaluate('y = 12345\n')

    repl.evaluate('y=2\n')
    with pytest.raises(ReplLimitError, match='SHN-R001'):
        repl.evaluate('z=3\n')


def test_repl_rejects_invalid_limit_configuration():
    with pytest.raises(ValueError):
        ReplLimits(max_snippet_chars=10, max_history_chars=5)
