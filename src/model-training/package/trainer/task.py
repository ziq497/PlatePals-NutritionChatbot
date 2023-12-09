import argparse
import os
import requests
import zipfile
import tarfile
import time
import datetime
from google.cloud import storage
from typing import Tuple, List, Dict

# Tensorflow
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.utils import to_categorical
from tensorflow.python.keras import backend as K
from tensorflow.python.keras.utils.layer_utils import count_params

# sklearn
from sklearn.model_selection import train_test_split

# Tensorflow Hub
import tensorflow_hub as hub

# Setup the arguments for the trainer task
parser = argparse.ArgumentParser()
parser.add_argument(
    "--model-dir", dest="model_dir", default="test", type=str, help="Model dir."
)
parser.add_argument("--lr", dest="lr", default=0.001, type=float, help="Learning rate.")
parser.add_argument(
    "--model_name",
    dest="model_name",
    default="mobilenetv2",
    type=str,
    help="Model name",
)
parser.add_argument(
    "--train_base",
    dest="train_base",
    default=False,
    action="store_true",
    help="Train base or not",
)
parser.add_argument(
    "--epochs", dest="epochs", default=10, type=int, help="Number of epochs."
)
parser.add_argument(
    "--batch_size", dest="batch_size", default=16, type=int, help="Size of a batch."
)
parser.add_argument(
    "--bucket_name",
    dest="bucket_name",
    default="",
    type=str,
    help="Bucket for data and models.",
)
args = parser.parse_args()

# TF Version
print("tensorflow version", tf.__version__)
print("Eager Execution Enabled:", tf.executing_eagerly())
# Get the number of replicas
strategy = tf.distribute.MirroredStrategy()
print("Number of replicas:", strategy.num_replicas_in_sync)

devices = tf.config.experimental.get_visible_devices()
print("Devices:", devices)
print(tf.config.experimental.list_logical_devices("GPU"))

print("GPU Available: ", tf.config.list_physical_devices("GPU"))
print("All Physical Devices", tf.config.list_physical_devices())

def download_blob(bucket_name: str, 
                  source_blob_name: str, 
                  destination_file_name: str) -> None:
    """
    Downloads a blob from the specified Google Cloud Storage bucket to a local file.

    Args:
        bucket_name (str): The name of the Google Cloud Storage bucket.
        source_blob_name (str): The name of the source blob (object) to download.
        destination_file_name (str): The local path where the downloaded blob should be saved.

    Returns:
        None
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    blob.download_to_filename(destination_file_name)

    print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")


def download_and_unzip_from_gcs(bucket_name: str, 
                                blob_name: str, 
                                destination_path: str) -> None:
    """
    Download and unzip a blob from Google Cloud Storage.

    Parameters:
        bucket_name (str): The name of the bucket.
        blob_name (str): The name of the blob (object) to download.
        destination_path (str): The path where the downloaded blob should be saved and extracted.

    Returns:
        None
    """
    
    # Initialize a storage client and get the bucket and blob
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    # Prepare the path to save the downloaded zip file
    zip_path = os.path.join(destination_path, blob_name.split('/')[-1])
    
    # Download the blob to the zip_path
    blob.download_to_filename(zip_path)
    print(f"Blob {blob_name} downloaded to {zip_path}.")
    
    # Extract the zip file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(destination_path)
    
    # Remove the downloaded zip file after extraction
    os.remove(zip_path)
    print(f"Data from {zip_path} extracted to {destination_path}.")


# Download Data
start_time = time.time()
#bucket_name = os.environ.get('GCS_BUCKET_URI', 'default-bucket-name')
bucket_name = "platepals-data"
data_version = "preprocessed_data"  # Example version
splits = ['train', 'val', 'test']  # Example splits

# Ensure that destination directories exist or create them
for split in splits:
    destination_path = os.path.join('./data')
    os.makedirs(destination_path, exist_ok=True)
    
    # Construct the blob name according to your previous structure
    blob_name = f"{data_version}/{split}.zip"
    
    # Download and unzip
    download_and_unzip_from_gcs(bucket_name, blob_name, destination_path)
end_time = time.time()
duration = (end_time - start_time) / 60
print(f"Download execution time {duration} minutes.")


def gather_data_from_directory(data_dir: str) -> Tuple[List[str], List[str]]:
    """
    Create a list of image paths and corresponding labels by scanning a directory.

    Parameters:
        data_dir (str): The directory path to scan for image data.

    Returns:
        Tuple[List[str], List[str]]: A tuple containing lists of image paths and labels.
    """
    
    image_paths = []
    labels = []

    for class_label in os.listdir(data_dir):
        class_path = os.path.join(data_dir, class_label)
        
        # Check if the path is a directory, skip if not
        if not os.path.isdir(class_path):
            continue

        for image_name in os.listdir(class_path):
            image_paths.append(os.path.join(class_path, image_name))
            labels.append(class_label)

    return image_paths, labels


def encode_labels(labels: List[str]) -> Tuple[List[int], Dict[str, int]]:
    """
    Encode a list of labels into integer values and create a label-to-index mapping.

    Parameters:
        labels (List[str]): A list of labels.

    Returns:
        Tuple[List[int], Dict[str, int]]: A tuple containing the encoded labels and the label-to-index mapping.
    """
    unique_labels = sorted(set(labels))
    label2index = {label: index for index, label in enumerate(unique_labels)}
    encoded_labels = [label2index[label] for label in labels]

    return encoded_labels, label2index

train_x, train_y = gather_data_from_directory("./data/train")
val_x, val_y = gather_data_from_directory("./data/val")
test_x, test_y = gather_data_from_directory("./data/test")

all_labels = train_y + val_y + test_y
all_encoded_labels, label2index = encode_labels(all_labels)

train_y_encoded = all_encoded_labels[:len(train_y)]
val_y_encoded = all_encoded_labels[len(train_y):len(train_y) + len(val_y)]
test_y_encoded = all_encoded_labels[len(train_y) + len(val_y):]
num_classes = len(label2index)

print("train_x count:", len(train_x))
print("validate_x count:", len(val_x))
print("test_x count:", len(test_x))
print("total classes:", num_classes)


def get_dataset(image_width: int = 128,
                image_height: int = 128,
                num_channels: int = 3,
                batch_size: int = 32,
                num_classes: int = 101) -> Tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset]:
    """
    Create TensorFlow datasets for training, validation, and testing.

    Parameters:
        image_width (int): Width of the image.
        image_height (int): Height of the image.
        num_channels (int): Number of color channels in the image.
        batch_size (int): Batch size for the datasets.
        num_classes (int): Number of target classes.

    Returns:
        Tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset]: A tuple of three TensorFlow datasets for training, validation, and testing.
    """
    
    # Load Image
    def load_image(path, label):
        image = tf.io.read_file(path)
        image = tf.image.decode_jpeg(image, channels=num_channels)
        image = tf.image.resize(image, [image_height, image_width])
        return image, label

    # Normalize pixels
    def normalize(image, label):
        image = image / 255
        return image, label

    train_shuffle_buffer_size = len(train_x)
    validation_shuffle_buffer_size = len(val_x)

    # Create TF Dataset
    train_data = tf.data.Dataset.from_tensor_slices((train_x, train_y_encoded))
    validation_data = tf.data.Dataset.from_tensor_slices((val_x, val_y_encoded))
    test_data = tf.data.Dataset.from_tensor_slices((test_x, test_y_encoded))


    # Train data
    train_data = train_data.shuffle(buffer_size=train_shuffle_buffer_size)
    train_data = train_data.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
    #train_data = train_data.map(normalize, num_parallel_calls=tf.data.AUTOTUNE)
    train_data = train_data.batch(batch_size)
    train_data = train_data.prefetch(tf.data.AUTOTUNE)

    # Validation data
    validation_data = validation_data.shuffle(buffer_size=validation_shuffle_buffer_size)
    validation_data = validation_data.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
    #validation_data = validation_data.map(normalize, num_parallel_calls=tf.data.AUTOTUNE)
    validation_data = validation_data.batch(batch_size)
    validation_data = validation_data.prefetch(tf.data.AUTOTUNE)

    # Test data
    test_data = test_data.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
    #test_data = test_data.map(normalize, num_parallel_calls=tf.data.AUTOTUNE)
    test_data = test_data.batch(batch_size)
    test_data = test_data.prefetch(tf.data.AUTOTUNE)

    return (train_data, validation_data, test_data)


# Efficient net model
def build_efficient_net(
    image_height: int,
    image_width: int,
    num_channels: int,
    num_classes: int,
    model_name: str,
    train_base: bool = False
) -> keras.models.Model:
    """
    Build a Keras model for image classification using the EfficientNet architecture.

    Parameters:
        image_height (int): Height of the input images.
        image_width (int): Width of the input images.
        num_channels (int): Number of color channels in the input images (e.g., 3 for RGB).
        num_classes (int): Number of target classes for classification.
        model_name (str): Name to assign to the created model.
        train_base (bool, optional): Whether to train the base layers of the EfficientNet model (default: False).

    Returns:
        keras.models.Model: A Keras model for image classification based on the EfficientNet architecture.
    """

    input_shape = (image_height,image_width,num_channels)
    base_model = tf.keras.applications.EfficientNetB0(include_top = False)
    base_model.trainable = train_base

    # Create functional model
    inputs = keras.layers.Input(shape=input_shape, name= "input_layer")

    x = base_model(inputs, training=False)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dense(num_classes)(x)
    outputs = keras.layers.Activation("softmax", dtype=tf.float32, name ="softmax_float32")(x)
    model = tf.keras.Model(inputs,outputs, name = model_name + "_train_base_" + str(train_base))
    #Get a summary of model
    return base_model, model

# Creating the tensoboard callback
def create_tensorboard_callback(dir_name,experiment):
  date_time = datetime.datetime.now().strftime('%Y/%m/%d:%H-%M-%S')
  path = os.path.join(dir_name,experiment,date_time)
  return tf.keras.callbacks.TensorBoard(log_dir=path)

print("Train model")
############################
# Training Params
############################
model_name = args.model_name
learning_rate = 0.001
image_width = 128
image_height = 128
num_channels = 3
batch_size = args.batch_size
epochs = args.epochs
train_base = False

# Free up memory
K.clear_session()

checkpoint_path = 'model_checkpoints/cp.cpkt'

checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(checkpoint_path,
                                                         monitor='val_accuracy',
                                                         save_best_only=True,
                                                         save_weights_only=True,
                                                         verbose=0)

# Data
train_data, validation_data, test_data = get_dataset(
    image_width=image_width,
    image_height=image_height,
    num_channels=num_channels,
    batch_size=batch_size,
    num_classes=num_classes 
)
print("Converted to Tensorflow dataset.")

# Model
base_model, model = build_efficient_net(
    image_height,
    image_width,
    num_channels,
    num_classes,
    model_name,
    train_base=train_base,
)
# Optimizer
#optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
optimizer = keras.optimizers.Adam()
# Loss
loss = keras.losses.sparse_categorical_crossentropy
# Print the model architecture
print(model.summary())
# Compile
model.compile(loss=loss, optimizer=optimizer, metrics=["accuracy"])

# Train model
start_time = time.time()
training_results = model.fit(
    train_data,
    steps_per_epoch=len(train_data),
    validation_data=validation_data,
    epochs=epochs,
    verbose=0,
    callbacks=[create_tensorboard_callback('models','FX_efficientnet0'),checkpoint_callback],
)

base_model.trainable = True
for layer in base_model.layers[:-20]:
  layer.trainable = False

model.compile(loss='sparse_categorical_crossentropy',
              optimizer=tf.keras.optimizers.Adam(1e-4),
              metrics=['accuracy'])

early_stopping = tf.keras.callbacks.EarlyStopping(monitor="val_loss",
                                                  patience=3)

checkpoint_path = "fine_tune_checkpoints/"
model_checkpoint = tf.keras.callbacks.ModelCheckpoint(checkpoint_path,
                                                      save_best_only=True,
                                                      monitor="val_loss")

reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss",  
                                                 factor=0.2,
                                                 patience=2,
                                                 verbose=1,
                                                 min_lr=1e-7)
                                            
best_model = model.fit(train_data,
                       epochs=100,
                       steps_per_epoch=len(train_data),
                       validation_data=validation_data,
                       callbacks=[create_tensorboard_callback('models','best_fine_effb0'),
                                  early_stopping,reduce_lr,model_checkpoint])

execution_time = (time.time() - start_time) / 60.0
print("Training execution time (mins)", execution_time)

ARTIFACT_URI = f"gs://{args.bucket_name}/model"

# Preprocess Image
def preprocess_image(bytes_input):
    decoded = tf.io.decode_jpeg(bytes_input, channels=3)
    decoded = tf.image.convert_image_dtype(decoded, tf.float32)
    resized = tf.image.resize(decoded, size=(128, 128))
    return resized

@tf.function(input_signature=[tf.TensorSpec([None], tf.string)])
def preprocess_function(bytes_inputs):
    decoded_images = tf.map_fn(
        preprocess_image, bytes_inputs, dtype=tf.float32, back_prop=False
    )
    return {"model_input": decoded_images}

@tf.function(input_signature=[tf.TensorSpec([None], tf.string)])
def serving_function(bytes_inputs):
    images = preprocess_function(bytes_inputs)
    results = model_call(**images)
    return results

model_call = tf.function(model.call).get_concrete_function(
    [
        tf.TensorSpec(
            shape=[None, 128, 128, 3], dtype=tf.float32, name="model_input"
        )
    ]
)

tf.saved_model.save(
    model,
    ARTIFACT_URI,
    signatures={"serving_default": serving_function},
)

print("Training Job Complete")
