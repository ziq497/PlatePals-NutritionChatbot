from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import asyncio
import pandas as pd
import os
from fastapi import File
from tempfile import TemporaryDirectory
from api import model
import json
import requests
import zipfile
import tensorflow as tf

# Setup FastAPI app
app = FastAPI(title="API Server", description="API Server", version="v1")

# Enable CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#Routes
@app.get("/")
async def get_index():
    return {"message": "Welcome to the API Service"}

@app.post("/predict")
async def predict(file: bytes = File(...)):
    print("predict file:", len(file), type(file))

    def download_file(packet_url, base_path="", extract=False, headers=None):
        if base_path != "":
            if not os.path.exists(base_path):
                os.mkdir(base_path)
        packet_file = os.path.basename(packet_url)
        with requests.get(packet_url, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(os.path.join(base_path, packet_file), "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        if extract:
            if packet_file.endswith(".zip"):
                with zipfile.ZipFile(os.path.join(base_path, packet_file)) as zfile:
                    zfile.extractall(base_path)
            else:
                packet_name = packet_file.split(".")[0]
                with tarfile.open(os.path.join(base_path, packet_file)) as tfile:
                    tfile.extractall(base_path)

    self_host_model = True
    
    if self_host_model:
        download_file(
            "https://github.com/amelialwx/models/releases/download/v2.0/model.zip",
            base_path="artifacts",
            extract=True,
        )
        artifact_dir = "./artifacts/model"

        # Load model
        prediction_model = tf.keras.models.load_model(artifact_dir) 

    # Save the image
    with TemporaryDirectory() as image_dir:
        image_path = os.path.join(image_dir, "test.png")
        with open(image_path, "wb") as output:
            output.write(file)

        # Make prediction
        prediction_results = {}
        labels = {
            "0": "apple_pie",
            "1": "baby_back_ribs",
            "2": "baklava",
            "3": "beef_carpaccio",
            "4": "beef_tartare",
            "5": "beet_salad",
            "6": "beignets",
            "7": "bibimbap",
            "8": "bread_pudding",
            "9": "breakfast_burrito",
            "10": "bruschetta",
            "11": "caesar_salad",
            "12": "cannoli",
            "13": "caprese_salad", 
            "14": "carrot_cake",
            "15": "ceviche",
            "16": "cheese_plate",
            "17": "cheesecake", 
            "18": "chicken_curry", 
            "19": "chicken_quesadilla",
            "20": "chicken_wings",
            "21": "chocolate_cake", 
            "22": "chocolate_mousse",
            "23": "churros",
            "24": "clam_chowder",
            "25": "club_sandwich",
            "26": "crab_cakes",
            "27": "creme_brulee",
            "28": "croque_madame",
            "29": "cup_cakes",
            "30": "deviled_eggs",
            "31": "donuts",
            "32": "dumplings",
            "33": "edamame",
            "34": "eggs_benedict",
            "35": "escargots",
            "36": "falafel",
            "37": "filet_mignon",
            "38": "fish_and_chips",
            "39": "foie_gras",
            "40": "french_fries",
            "41": "french_oinion_soup",
            "42": "french_toast",
            "43": "fried_calamari",
            "44": "fried_rice",
            "45": "frozen_yogurt",
            "46": "garlic_bread",
            "47": "gnocchi",
            "48": "greek_salad",
            "49": "grilled_cheese_sandwich",
            "50": "grilled_salmon",
            "51": "guacamole",
            "52": "gyoza",
            "53": "hamburger",
            "54": "hot_and_sour_soup",
            "55": "hot_dog",
            "56": "huevos_rancheros", 
            "57": "hummus",
            "58": "ice_cream",
            "59": "lasagna",
            "60": "lobster_bisque",
            "61": "lobster_roll_sandwich",
            "62": "macaroni_and_cheese",
            "63": "macarons",
            "64": "miso_soup",
            "65": "mussels",
            "66": "nachos",
            "67": "omelette",
            "68": "onion_rings",
            "69": "oysters",
            "70": "pad_thai",
            "71": "paella",
            "72": "pancakes",
            "73": "panna_cotta",
            "74": "peking_duck", 
            "75": "pho",
            "76": "pizza",
            "77": "pork_chop",
            "78": "poutine",
            "79": "prime_rib",
            "80": "pulled_pork_sandwich",
            "81": "ramen", 
            "82": "ravioli",
            "83": "red_velvet_cake",
            "84": "risotto",
            "85": "samosa",
            "86": "sashimi",
            "87": "scallops",
            "88": "seaweed_salad",
            "89": "shrimp_and_grits",
            "90": "spaghetti_bolognese",
            "91": "spaghetti_carbonara",
            "92": "spring_rolls",
            "93": "steak",
            "94": "strawberry_shortcake",
            "95": "sushi",
            "96": "tacos",
            "97": "takoyaki",
            "98": "tiramusi",
            "99": "tuna_tartare",
            "100": "waffles"
            }
        if self_host_model:
            prediction_results = model.make_prediction(image_path, prediction_model, labels)
        else:
            prediction_results = model.make_prediction_vertexai(image_path, labels)

    print(prediction_results)
    return prediction_results

@app.get("/status")
async def get_api_status():
    return {
        "version": "0.2",
        "tf_version": tf.__version__,
    }