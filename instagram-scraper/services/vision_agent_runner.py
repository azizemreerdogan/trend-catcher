from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VisionAgentRunResult:
    triggered: bool
    return_code: int


class VisionAgentRunner:
    def __init__(self, project_root: str | Path) -> None:
        self._project_root = Path(project_root)
        self._vision_agent_dir = self._project_root / "vision-agent"
        self._entrypoint = self._vision_agent_dir / "main.py"
        self._python_executable = self._resolve_python_executable()

    def run(self, video_id: str) -> VisionAgentRunResult:
        completed = subprocess.run(
            [str(self._python_executable), str(self._entrypoint), video_id],
            cwd=str(self._vision_agent_dir),
            check=False,
        )
        return VisionAgentRunResult(triggered=True, return_code=completed.returncode)

    def _resolve_python_executable(self) -> Path:
        venv_python = self._project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            return venv_python
        return Path(sys.executable)
