from gui import LUMEModelVisualApp
from dotenv import load_dotenv
from util import get_model_path, initialize_logger

load_dotenv()  # Load environment variables from .env file

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
    model_file_path = get_model_path("LCLS_FEL_Surrogate")
    logger.info(f"Using model file at: {model_file_path}")

    app = LUMEModelVisualApp(model_file_path, PV_OUTPUT_NAMES)
    app.start()


if __name__ == "__main__":
    main()
