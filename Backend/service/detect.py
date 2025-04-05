import torch
import torchvision
from torchvision import transforms
from torch.utils.data.dataset import Dataset
import numpy as np
import cv2
import face_recognition
from torch import nn
from torchvision import models
import warnings
import os
import logging

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


class Model(nn.Module): # Made a class for our custom neural network
    def __init__(self, num_classes, latent_dim=2048, lstm_layers=1, hidden_dim=2048, bidirectional=False): #set layers
        super(Model, self).__init__()
        model = models.resnext50_32x4d(pretrained=True) #called cnn resnext feature extraction
        self.model = nn.Sequential(*list(model.children())[:-2]) # removed last two layers to focus on feature extraction
        self.lstm = nn.LSTM(latent_dim, hidden_dim, lstm_layers, bidirectional) # defined lstm for sequential [processing]
        self.relu = nn.LeakyReLU()
        self.dp = nn.Dropout(0.4) # prevents overfitting
        self.linear1 = nn.Linear(2048, num_classes) 
        self.avgpool = nn.AdaptiveAvgPool2d(1)

    def forward(self, x):  # defines how data flows forward through the model
        batch_size, seq_length, c, h, w = x.shape
        x = x.view(batch_size * seq_length, c, h, w) #flatten 
        fmap = self.model(x) # feature extraction
        x = self.avgpool(fmap)
        x = x.view(batch_size, seq_length, 2048) # reshaping for lstm
        x_lstm, _ = self.lstm(x, None)
        return fmap, self.dp(self.linear1(x_lstm[:, -1, :])) #finally the classification


# Required transformations of input 
im_size = 112
mean = [0.485, 0.456, 0.406]
std = [0.229, 0.224, 0.225]

train_transforms = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((im_size, im_size)),
    transforms.ToTensor(),
    transforms.Normalize(mean, std)
])

# Dataset Class for Processing Videos
class ValidationDataset(Dataset):
    def __init__(self, video_names, sequence_length=60, transform=None):  # video preprossesing
        self.video_names = video_names
        self.transform = transform

        self.count = sequence_length

    def __len__(self):
        return len(self.video_names)

    def __getitem__(self, idx): # get frames from video and face detection
        video_path = self.video_names[idx]
        frames = []
        try:
            for i, frame in enumerate(self.frame_extract(video_path)):
                faces = face_recognition.face_locations(frame)
                try:
                    top, right, bottom, left = faces[0]
                    frame = frame[top:bottom, left:right, :]
                except:
                    logger.warning(f"No face detected in frame {i}")
                frames.append(self.transform(frame))
                if len(frames) == self.count:
                    break
        except Exception as e:
            logger.error(f"Error processing video frames: {str(e)}")
            raise

        if not frames:
            raise ValueError("No frames were successfully processed from the video")

        frames = torch.stack(frames)
        frames = frames[:self.count]
        return frames.unsqueeze(0)

    def frame_extract(self, path): #function for frame extraction 
        vidObj = cv2.VideoCapture(path)
        if not vidObj.isOpened():
            raise FileNotFoundError(f"Unable to open video file {path}")
        success = True
        while success:
            success, image = vidObj.read()
            if success:
                yield image
        vidObj.release()


def predict(model, img):
    model.eval()
    with torch.no_grad():
        fmap, logits = model(img.to("cpu")) 
        sm = nn.Softmax(dim=1)
        logits = sm(logits)
        _, prediction = torch.max(logits, 1)
        confidence = logits[:, int(prediction.item())].item() * 100
        return [int(prediction.item()), confidence]



def detect_fake_video(video_path): 
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(os.path.dirname(current_dir), 'service', 'df_model.pt')
    video_path = os.path.abspath(video_path)
    logger.info(f"Current directory: {current_dir}")
    logger.info(f"Loading model from: {model_path}")
    logger.info(f"Model exists: {os.path.exists(model_path)}")
    
    if not os.path.exists(model_path):
        error_msg = f"Model file not found at {model_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    if not os.path.exists(video_path):
        error_msg = f"Video file not found at {video_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        logger.info("Initializing model...")
        model = Model(2)  # Binary classification (real/fake)
        logger.info("Loading model state dict...")
        model.load_state_dict(torch.load(model_path, map_location=torch.device("cpu")))  # Load on CPU
        model.eval()
        logger.info("Model loaded successfully")

        logger.info("Creating dataset...")
        dataset = ValidationDataset([video_path], sequence_length=20, transform=train_transforms)
        logger.info("Dataset created successfully")

        logger.info("Processing video...")
        prediction = predict(model, dataset[0])
        logger.info(f"Raw prediction: {prediction}")

        result = "REAL" if prediction[0] == 1 else "FAKE"
        logger.info(f"Detection completed: {result} (Confidence: {prediction[1]:.2f}%)")
        
        return prediction

    except Exception as e:
        logger.error(f"Error during detection: {str(e)}")
        logger.exception("Full traceback:")
        raise


# if __name__ == "__main__": 
#     video_filename = "Fake.mp4"  
#     video_path = f'./{video_filename}'
#     # print(video_path)
#     detect_fake_video(video_path)
#     if os.path.exists(video_path):
#         detect_fake_video(video_path)
#     else:
#         logger.error(f"Video file {video_filename} not found in the current directory!")

