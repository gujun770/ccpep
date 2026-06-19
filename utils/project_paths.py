from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "dataset"
HELM_DIR = ROOT_DIR / "HELM"
MODEL_DIR = ROOT_DIR / "model"
RESULT_DIR = ROOT_DIR / "Result"


def env_or_default(env_name: str, default: Path) -> str:
    value = os.getenv(env_name)
    return value if value else str(default)


def resolve_path(*parts: str) -> str:
    return str(ROOT_DIR.joinpath(*parts))


def resolve_dataset_path(*parts: str) -> str:
    return str(DATASET_DIR.joinpath(*parts))


def resolve_model_path(*parts: str) -> str:
    return str(MODEL_DIR.joinpath(*parts))

