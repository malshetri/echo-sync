"""
Tests for FR-10 eyes-free onboarding wizard.

Focus on the run-decision logic (should_run) without touching audio or the
real marker file on disk.
"""

from echo_sync.config.settings import Settings
from echo_sync.interaction.onboarding import OnboardingWizard


class _FakeEarcons:
    def play_success(self) -> None:
        pass

    def play_listening(self) -> None:
        pass


def _make_wizard() -> OnboardingWizard:
    return OnboardingWizard(
        settings=Settings(),
        respond=lambda text: None,
        earcons=_FakeEarcons(),
        console=object(),
        demo_keyboard=True,
    )


class TestShouldRun:
    def test_skip_always_wins(self):
        wizard = _make_wizard()
        assert wizard.should_run(force=True, skip=True) is False

    def test_force_runs_even_when_complete(self, monkeypatch):
        wizard = _make_wizard()
        monkeypatch.setattr(OnboardingWizard, "is_complete", staticmethod(lambda: True))
        assert wizard.should_run(force=True, skip=False) is True

    def test_runs_when_not_complete(self, monkeypatch):
        wizard = _make_wizard()
        monkeypatch.setattr(OnboardingWizard, "is_complete", staticmethod(lambda: False))
        assert wizard.should_run() is True

    def test_skips_when_complete(self, monkeypatch):
        wizard = _make_wizard()
        monkeypatch.setattr(OnboardingWizard, "is_complete", staticmethod(lambda: True))
        assert wizard.should_run() is False
