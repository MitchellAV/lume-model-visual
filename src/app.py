import os
from gui import LUMEModelVisualApp
from dotenv import load_dotenv
from utils import get_model_path, initialize_logger

env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

load_dotenv(env_file_path)  # Load environment variables from .env file

logger = initialize_logger(__name__)

PV_OUTPUT_NAMES = [
    "OTRS:IN20:571:XRMS_CU_HXR_LUME",
    "OTRS:IN20:571:YRMS_CU_HXR_LUME",
    "OTRS:IN20:571:EMITN_X_CU_HXR_LUME",
    "OTRS:IN20:571:EMITN_Y_CU_HXR_LUME",
    "OTRS:IN20:571:EMIT_X_CU_HXR_LUME",
    "OTRS:IN20:571:EMIT_Y_CU_HXR_LUME",
    "OTRS:IN20:571:ZRMS_CU_HXR_LUME",
]


def main() -> None:
    model_file_path = get_model_path("lcls_cu_injector_ml_model")
    logger.info(f"Using model file at: {model_file_path}")

    print("ENVs loaded from dotenv")
    envs = {
        key: value
        for key, value in dict(**os.environ).items()
        if key.startswith("TRAME")
    }
    logger.info(f"TRAME-related environment variables: {envs}")

    app = LUMEModelVisualApp(model_file_path, PV_OUTPUT_NAMES)

    app.start()  # Start the app in a separate thread to allow for graceful shutdown


if __name__ == "__main__":
    main()
