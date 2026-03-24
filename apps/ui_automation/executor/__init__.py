from .base import BaseTestExecutor
from .appium_runner import AppiumRunnerMixin
from .playwright_runner import PlaywrightRunnerMixin
from .selenium_runner import SeleniumRunnerMixin
from .airtest_runner import AirtestRunnerMixin
from .ai_runner import AIRunnerMixin
from .minium_runner import MiniumRunnerMixin

class TestExecutor(AppiumRunnerMixin, PlaywrightRunnerMixin, SeleniumRunnerMixin, AirtestRunnerMixin, AIRunnerMixin, MiniumRunnerMixin, BaseTestExecutor):
    pass
