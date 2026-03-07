import os
from gui import LUMEModelVisualApp
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


def get_model_path(model_name: str) -> str:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MODELS_DIR = os.path.join(BASE_DIR, "models")
    MODEL_PATH = os.path.join(MODELS_DIR, f"{model_name}")

    MODEL_YAML_PATH = os.path.join(MODEL_PATH, "model_config.yaml")
    if not os.path.exists(MODEL_YAML_PATH):
        raise FileNotFoundError(
            f"Model configuration file not found at {MODEL_YAML_PATH}"
        )

    return MODEL_YAML_PATH


def main() -> None:
    model_file_path = get_model_path("LCLS_FEL_Surrogate")

    app = LUMEModelVisualApp(model_file_path)
    app.start()


if __name__ == "__main__":
    main()
