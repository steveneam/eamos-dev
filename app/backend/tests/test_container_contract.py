from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = BACKEND_ROOT / "Dockerfile"
DOCKERIGNORE = BACKEND_ROOT / ".dockerignore"
RUNTIME_IDENTITY = "1000:1000"


def _top_level_instructions() -> list[str]:
    return [
        line.strip()
        for line in DOCKERFILE.read_text(encoding="utf-8").splitlines()
        if line and not line[0].isspace() and not line.startswith("#")
    ]


def test_container_runtime_identity_is_the_final_numeric_user() -> None:
    instructions = _top_level_instructions()
    users = [line.removeprefix("USER ") for line in instructions if line.startswith("USER ")]

    assert users == [RUNTIME_IDENTITY]
    assert instructions.index(f"USER {RUNTIME_IDENTITY}") < instructions.index("EXPOSE 8000")
    assert instructions.index(f"USER {RUNTIME_IDENTITY}") < next(
        index for index, line in enumerate(instructions) if line.startswith("CMD ")
    )


def test_container_prepares_only_runtime_writable_paths_before_user_switch() -> None:
    dockerfile = " ".join(DOCKERFILE.read_text(encoding="utf-8").split())
    user_switch = dockerfile.index(f"USER {RUNTIME_IDENTITY}")
    before_user = dockerfile[:user_switch]

    assert "HOME=/home/eamos" in before_user
    assert "mkdir -p /home/eamos /app/data/uploads /app/data/final_reports" in before_user
    assert f"chown -R {RUNTIME_IDENTITY} /home/eamos /app/data" in before_user


def test_container_build_context_excludes_local_credentials_and_tooling() -> None:
    exclusions = {
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert {".env", ".git", ".venv"} <= exclusions
