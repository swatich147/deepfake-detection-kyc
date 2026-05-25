"""Minimal evaluation stub — Phase 4 ML pipeline placeholder (no training cost)."""
import json
from pathlib import Path


def main():
    config_path = Path(__file__).resolve().parents[1] / "ai_service" / "model_config.yaml"
    print("Model registry (read-only demo):")
    if config_path.is_file():
        print(config_path.read_text())
    else:
        print(json.dumps({"status": "model_config.yaml not found"}, indent=2))
    print("\nTo add real models: place weights in ai_service/weights/ and set MOCK_INFERENCE=false")


if __name__ == "__main__":
    main()
