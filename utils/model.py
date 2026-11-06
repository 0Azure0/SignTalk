import pickle

from utils.feature_extraction import normalize_hand_features


class ASLClassificationModel:
    @staticmethod
    def load_model(model_path):
        # Load model and mapping from pickle
        with open(model_path, "rb") as file:
            model, mapping = pickle.load(file)

        if model is not None:
            return ASLClassificationModel(model, mapping)

        raise Exception("Model not loaded correctly!")

    def __init__(self, model, mapping):
        self.model = model
        self.mapping = mapping

    def predict(self, feature):
        normalized_feature = normalize_hand_features(feature)
        return self.mapping[
            self.model.predict(normalized_feature.reshape(1, -1)).item()
        ]