from lume_model.models import TorchModel

LCLS_CU_INJECTOR_MODEL_PATH = "lcls_cu_injector_ml_model"


def main() -> None:
    model_file_path = LCLS_CU_INJECTOR_MODEL_PATH + "/model_config.yaml"
    model = TorchModel(model_file_path)

    result = model.evaluate({"QUAD:IN20:425:BACT": -1})
    print(result)


if __name__ == "__main__":
    main()
