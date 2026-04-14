"""Unit tests for sdk/utils/complexity.py — ComplexityClassifier."""

import pytest

from sdk.utils.complexity import ComplexityClassifier


@pytest.mark.unit
class TestComplexityClassifier:

    def test_micro_task_is_level1(self):
        result = ComplexityClassifier.classify("fix typo in README")
        assert result.level == 1
        assert result.fast_track is True

    def test_auth_task_is_level2(self):
        result = ComplexityClassifier.classify("add JWT authentication to the REST API")
        assert result.level == 2
        assert result.fast_track is False

    def test_ambiguous_objective_is_level2(self):
        result = ComplexityClassifier.classify("maybe add logging or fix the bug?")
        assert result.level == 2

    def test_many_files_is_level2(self):
        result = ComplexityClassifier.classify(
            "update app/models/user.py app/services/auth.py app/routers/api.py app/tests/test_auth.py"
        )
        assert result.level == 2

    def test_short_unambiguous_is_level1(self):
        result = ComplexityClassifier.classify("rename variable in config.py")
        assert result.level == 1

    def test_payment_keyword_is_level2(self):
        result = ComplexityClassifier.classify("integrate Stripe payment processing")
        assert result.level == 2
        assert result.reason == "architectural scope"
