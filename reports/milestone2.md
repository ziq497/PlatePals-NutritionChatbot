AC215 - Milestone 2 (PlatePals)
==============================
**Team Members**

- Amelia Li
- Rebecca Qiu
- Peter Wu

**Group Name**

PlatePals

**Project**

The goal of this project is to develop a machine learning application that accurately identifies the types of food present in a user-uploaded image. Based on the foods identified, the application will provide the user with relevant nutritional information and personalized dietary recommendations. This project will involve key phases of data preprocessing, model development, and application interface development, leveraging TensorFlow's Food-101 dataset.

### Milestone 2 ###

We'll predominantly employ TensorFlow's Food-101 dataset, featuring 101,000 annotated food images across 101 categories. Additionally, we will correlate the identified food items with nutritional metrics obtained from Kaggle's Nutrition datasets and a database called Nutritional Facts for Most Common Foods, which together offer around 9,000 nutritional records. Our dataset is securely hosted in a private Google Cloud Bucket.

Project Organization
------------
      ├── LICENSE
      ├── README.md
      ├── notebooks
      ├── references
      ├── requirements.txt
      ├── setup.py
      ├── reports
      └── src
            |── preprocessing
                ├── Dockerfile
                ├── docker-entrypoint.sh
                ├── docker-shell.bat
                ├── docker-shell.sh
                ├── preprocess.py
                └── requirements.txt
Preprocess container
------------
- This container ingests 4.65GB of the [Food-101 dataset](https://www.tensorflow.org/datasets/catalog/food101) and performs image preprocessing before uploading the modified data to a GCS Bucket.
- It also fetches and uploads [nutritional data](https://raw.githubusercontent.com/prasertcbs/basic-dataset/master/nutrients.csv) as a CSV file to the same GCS Bucket.
- Required inputs: GCS Project Name and GCS Bucket Name.
- Output: Processed data stored in the GCS Bucket.

(1) `src/preprocessing/preprocess.py`: This file manages the preprocessing of our 4.65GB dataset. Image dimensions are resized to 128x128 pixels to expedite subsequent processing. We apply random transformations such as horizontal flips, rotations, and zooms. These preprocessed images are batch-processed and uploaded to the GCS Bucket as a zip file.

(2) `src/preprocessing/requirements.txt`: Lists the Python packages essential for image preprocessing.

(3) `src/preprocessing/Dockerfile`: The Dockerfile is configured to use `python:3.9-slim-buster`. It sets up volumes and uses secret keys (which should not be uploaded to GitHub) for connecting to the GCS Bucket.

Running our code
------------
**Setup GCP Service Account**
1. Create a secrets folder that is on the same level as the project folder.
2. Head to [GCP Console](https://console.cloud.google.com/home/dashboard).
3. Search for "Service Accounts" from the top search box OR go to: "IAM & Admins" > "Service Accounts" and create a new service account called "PlatePals". 
4. For "Grant this service account access to project", select "Cloud Storage" > "Storage Object Viewer"
5. Click done. This will create a service account.
6. Click on the "..." under the "Actions" column and select "Manage keys".
7. Click on "ADD KEY" > "Create new key" with "Key type" as JSON.
8. Copy this JSON file into the secrets folder created in step 1 and rename it as "data-service-account.json".

**Setup GCS Bucket**
1. Head to [GCP Console](https://console.cloud.google.com/home/dashboard).
2. Search for "Buckets" from the top search box OR go to: "Cloud Storage" > "Buckets" and create a new bucket with an appropriate bucket name e.g. "platepals-test".
3. Click done. This will create a new GCS Bucket.

**Set GCP Credentials**
1. Head to src/preprocessing/docker-shell.sh.
2. Replace `GCS_BUCKET_NAME` and `GCP_PROJECT` with corresponding GCS Bucket Name that you have chosen above and GCP Project Name.
3. Repeat step 2 for src/preprocessing/docker-shell.bat.

**Execute Dockerfile**
1. Make sure the Docker application is operational.
2. **NOTE: EXECUTION MAY TAKE 2-3 HOURS DEPENDING ON NETWORK SPEED.** Navigate to src/preprocessing and execute `sh docker-shell.sh`.
3. Upon completion, your GCS Bucket should display the processed data as shown under the default folder name "version1".
![bucket-data](assets/bucket-data.png)

DVC Setup
------------
This step is entirely optional.
1. Make sure dvc[gs] is installed by running `pip install dvc[gs]`.
2. Initialize git at the root of the file by running `git init`.
3. Initialize dvc at the root of the file by running `dvc init`.
2. Ensure that the gcloud CLI is installed by running a gcloud command e.g. `gcloud projects list`. [Instructions](https://cloud.google.com/sdk/docs/install) for installation can be found here.
3. Run the command `gcloud auth application-default login` to be authenticated with the gcloud CLI.
4. Run the command `dvc import-url gs://{GCS_BUCKET_NAME}/version1`.
5. Run the command `git add .gitignore version1.dvc`
6. Run `git commit -m "added raw data"`.
9. You have now committed the latest version of the data using dvc.


Challenges and Future Directions
------------

1. **Data Transfer Time**: We've observed that the data download and upload process currently takes between 2-3 hours. Although we've optimized the process to some extent, we aim to investigate further to determine whether these durations can be shortened. This is on our agenda for the next milestone.

2. **Remote Data and DVC Integration**: Our attempts to integrate DVC have been unsuccessful due to the remote storage of our dataset in a GCS Bucket. The in-class examples primarily utilize locally-stored data, making our remote setup a complicating factor. We're exploring alternative solutions, such as employing `gcsfuse` to potentially mount our GCS Bucket, to address this challenge.