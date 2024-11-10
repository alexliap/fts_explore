import gdown

# insert the shareable URL of a Drive folder to download
url = "https://drive.google.com/drive/folders/1Qi8Oh4qyirVh2zacrvyADJVXvy8z3PCr?usp=drive_link"
gdown.download_folder(url)
