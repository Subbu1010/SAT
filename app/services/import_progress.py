from __future__ import annotations

from typing import Protocol


class ImportProgressReporter(Protocol):
    def step(self, message: str) -> None: ...

    def detail(self, message: str) -> None: ...


class NoOpImportProgress:
    def step(self, message: str) -> None:
        return None

    def detail(self, message: str) -> None:
        return None


class CollectingImportProgress:
    """Stores progress messages for tests or post-run display."""

    def __init__(self) -> None:
        self.steps: list[str] = []
        self.details: list[str] = []

    def step(self, message: str) -> None:
        self.steps.append(message)

    def detail(self, message: str) -> None:
        self.details.append(message)

    @property
    def log(self) -> list[str]:
        return [*self.steps, *[f"  {line}" for line in self.details]]


class StreamlitImportProgress:
    def __init__(self, status_container, *, collecting: CollectingImportProgress | None = None) -> None:
        self._status = status_container
        self._collecting = collecting or CollectingImportProgress()
        self._step_num = 0

    @property
    def log(self) -> list[str]:
        return self._collecting.log

    def step(self, message: str) -> None:
        self._step_num += 1
        self._collecting.step(message)
        self._status.write(f"**Step {self._step_num}:** {message}")
        self._status.update(label=message, state="running")

    def detail(self, message: str) -> None:
        self._collecting.detail(message)
        self._status.write(f"↳ {message}")
