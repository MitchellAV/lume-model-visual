from gui import LUMEModelVisualApp

MODEL_PATH = (
    "/Users/mvicto/Desktop/projects/lume/lume-model-visual/lcls_cu_injector_ml_model"
)


def main() -> None:
    model_file_path = MODEL_PATH + "/model_config.yaml"

    app = LUMEModelVisualApp(model_file_path)
    app.start()


if __name__ == "__main__":
    main()
