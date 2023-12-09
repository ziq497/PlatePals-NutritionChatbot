import os
import zipfile
import io
import requests
import argparse
import tensorflow as tf
import tensorflow_datasets as tfds
from tensorflow.keras.layers.experimental import preprocessing
from google.cloud import storage

IMG_SIZE = 128

# GCS
# BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'default-bucket-name')
BUCKET_NAME = "platepals-data" # CHANGE THIS
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

# Constants for nutrients dataset
NUTRIENTS_URL = "https://raw.githubusercontent.com/prasertcbs/basic-dataset/master/nutrients.csv"
LOCAL_PATH, GCS_OBJECT_NAME = "nutrients.csv", "nutrients.csv"
DATA_VERSION = "preprocessed_data" # UPDATE THIS IF NEEDED


def data_augmentation_layer() -> tf.keras.Sequential:
    """
    Create a Keras Sequential model for data augmentation.
    
    Returns:
        A Keras Sequential model for data augmentation.
    """
    return tf.keras.Sequential([
        preprocessing.RandomFlip('horizontal'),
        preprocessing.RandomRotation(0.2),
        preprocessing.RandomZoom(0.2),
        preprocessing.RandomHeight(0.2),
        preprocessing.RandomWidth(0.2)
    ], name="data_augmentation")


def preprocess_img(image: tf.Tensor, label: tf.Tensor, 
                   img_size: int = IMG_SIZE, 
                   augment_layer: tf.keras.Sequential = None) -> tuple[tf.Tensor, tf.Tensor]:
    """
    Preprocess an image and its label.

    Args:
        image (tf.Tensor): The input image tensor.
        label (tf.Tensor): The label tensor.
        img_size (int, optional): The target image size. Defaults to IMG_SIZE.
        augment_layer (tf.keras.Sequential, optional): An optional data augmentation layer. Defaults to None.

    Returns:
        tuple[tf.Tensor, tf.Tensor]: A tuple containing the preprocessed image and its label.
    """
    if augment_layer:
        image = augment_layer(image)
    image = tf.image.resize(image, [img_size, img_size])
    return tf.cast(image, tf.float32), label


def fetch_and_process_dataset(split_list: list[str], 
                              ds_info: tfds.core.DatasetInfo, 
                              augment_layer: tf.keras.Sequential) -> None:
    """
    Fetch and preprocess a dataset for a list of splits.

    Args:
        split_list (list[str]): A list of split names (e.g., 'train', 'val', 'test').
        ds_info (tfds.core.DatasetInfo): Information about the dataset.
        augment_layer (tf.keras.Sequential): A data augmentation layer.
    
    Returns:
        None
    """
    
    split_to_name = {
        'train': 'train',
        'validation[:40%]': 'val',
        'validation[40%:]': 'test'
    }
    
    datasets = {}
    for tfds_split, custom_split in split_to_name.items():
        ds = tfds.load('food101', split=tfds_split, as_supervised=True)
        ds = ds.map(lambda img, lbl: preprocess_img(img, lbl, augment_layer=augment_layer),
                    num_parallel_calls=tf.data.AUTOTUNE)
        ds = ds.shuffle(buffer_size=1000).batch(batch_size=32).prefetch(tf.data.AUTOTUNE)
        datasets[custom_split] = ds

    for custom_split, ds in datasets.items():
        create_zip_and_upload(ds, ds_info, custom_split)


# Function to zip and upload preprocessed images to GCS
def create_zip_and_upload(ds: tf.data.Dataset, 
                          ds_info: tfds.core.DatasetInfo, 
                          split: str) -> None:
    """
    Create a ZIP of preprocessed images and upload it to Google Cloud Storage (GCS).

    Args:
        ds (tf.data.Dataset): The dataset containing preprocessed images and labels.
        ds_info (tfds.core.DatasetInfo): Information about the dataset.
        split (str): The name of the dataset split (e.g., 'train', 'val', 'test').

    Returns:
        None
    """
    
    zip_buffer = io.BytesIO()
    # Keep track of generated file names to avoid duplicates
    seen_files = set()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img_batch_idx, (img_batch, label_batch) in enumerate(ds): 
            for img_idx, (img, label) in enumerate(zip(img_batch, label_batch)):
                label_str = ds_info.features['label'].int2str(label.numpy())
                # Loop until we generate a unique file name
                while True:
                    file_name = f"{split}/{label_str}/{img_batch_idx}_{img_idx}_{tf.random.uniform(shape=[], minval=1, maxval=int(1e7), dtype=tf.int32)}.jpg"
                    if file_name not in seen_files:
                        break
                seen_files.add(file_name)
                # Cast the image to uint8 before encoding
                img_uint8 = tf.cast(img, tf.uint8)
                img_encoded = tf.image.encode_jpeg(img_uint8)
                zf.writestr(file_name, img_encoded.numpy())
    
    zip_buffer.seek(0)
    blob_name = f"{DATA_VERSION}/{split}.zip"
    #client = storage.Client.from_service_account_json(GOOGLE_APPLICATION_CREDENTIALS)
    client = storage.Client()
    bucket = client.get_bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.chunk_size = 5 * 1024 * 1024
    blob.upload_from_file(zip_buffer, content_type='application/zip')


# Function to download the nutrients dataset
def download_nutrients_dataset(url: str, local_path: str) -> None:
    """
    Download a nutrients dataset from a URL and save it locally.

    Args:
        url (str): The URL of the nutrients dataset.
        local_path (str): The local path where the dataset will be saved.
        
    Returns: 
        None
    """
    if os.path.exists(local_path):
        os.remove(local_path)

    response = requests.get(url)
    response.raise_for_status()
    
    with open(local_path, "wb") as f:
        f.write(response.content)


# Function to upload nutrients dataset to GCS
def upload_nutrients_to_gcs(bucket_name: str, 
                            source_file: str, 
                            destination_blob_name: str) -> None:
    """
    Upload a nutrients dataset from a local file to Google Cloud Storage (GCS).

    Args:
        bucket_name (str): The name of the GCS bucket.
        source_file (str): The local file to be uploaded.
        destination_blob_name (str): The name of the destination blob in GCS.

    Returns: 
        None
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"{DATA_VERSION}/{destination_blob_name}")  
    blob.upload_from_filename(source_file)
    os.remove(source_file)


if __name__ == "__main__":
    augment_layer = data_augmentation_layer()
    ds_info = tfds.builder('food101').info
    fetch_and_process_dataset(['train', 'validation[:40%]', 'validation[40%:]'], ds_info, augment_layer)
    download_nutrients_dataset(NUTRIENTS_URL, LOCAL_PATH)
    upload_nutrients_to_gcs(BUCKET_NAME, LOCAL_PATH, GCS_OBJECT_NAME)
    
    print(f"Preprocessed and augmented data uploaded to GCS bucket {BUCKET_NAME}.")