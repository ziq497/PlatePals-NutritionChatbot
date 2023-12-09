import os
import json
import numpy as np
import tensorflow as tf
from google.cloud import aiplatform
from tensorflow.keras.preprocessing import image
import base64
from collections import Counter

def center_crop(x, center_crop_size):
    centerw, centerh = x.shape[0]//2, x.shape[1]//2
    halfw, halfh = center_crop_size[0]//2, center_crop_size[1]//2
    return x[centerw-halfw:centerw+halfw, centerh-halfh:centerh+halfh, :]

def predict_10_crop(img, model, top_n=5):
    crop_size = (224, 224)
    flipped_X = np.fliplr(img)

    # Create 10 crops
    crops = [
        img[:crop_size[0], :crop_size[1], :],  # Upper Left
        img[:crop_size[0], -crop_size[1]:, :], # Upper Right
        img[-crop_size[0]:, :crop_size[1], :], # Lower Left
        img[-crop_size[0]:, -crop_size[1]:, :],# Lower Right
        center_crop(img, crop_size),           # Center
        flipped_X[:crop_size[0], :crop_size[1], :],  # Flipped Upper Left
        flipped_X[:crop_size[0], -crop_size[1]:, :], # Flipped Upper Right
        flipped_X[-crop_size[0]:, :crop_size[1], :], # Flipped Lower Left
        flipped_X[-crop_size[0]:, -crop_size[1]:, :],# Flipped Lower Right
        center_crop(flipped_X, crop_size)            # Flipped Center
    ]

    # Resize crops
    crops = [tf.image.resize(crop, (224, 224)) for crop in crops]

    # Model prediction
    y_pred = model.predict(np.stack(crops, axis=0))
    preds = np.argmax(y_pred, axis=1)
    top_n_preds = np.argpartition(y_pred, -top_n)[:,-top_n:]

    return preds, top_n_preds


def make_prediction(image_path, my_model, index2label):

    print("Predict using self-hosted model")

    img = image.load_img(image_path)
    img_array = image.img_to_array(img)

    preds, top_n_preds = predict_10_crop(img_array, my_model)
    most_common_pred, count = Counter(preds).most_common(1)[0]
    prediction_label = index2label[str(most_common_pred)]

    return {
        "prediction_label": prediction_label,
    }


def make_prediction_vertexai(image_path, index2label):
    print("Predict using Vertex AI endpoint")

    # Get the endpoint
    endpoint = aiplatform.Endpoint(
        "projects/543953613952/locations/us-central1/endpoints/98078636220874752"
    )

    with open(image_path, "rb") as f:
        data = f.read()
    b64str = base64.b64encode(data).decode("utf-8")
    instances = [{"bytes_inputs": {"b64": b64str}}]

    result = endpoint.predict(instances=instances)

    print("Result:", result)
    prediction = result.predictions[0]
    print(prediction, prediction.index(max(prediction)))

    prediction_label = index2label[str(prediction.index(max(prediction)))]

    return {
        "prediction_label": prediction_label,
        "prediction": prediction,
        "accuracy": round(np.max(prediction) * 100, 2),
    }