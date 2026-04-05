import torch
import torch.nn as nn
import torch.optim as optim

from ml.model import LSTMModel
from ml.config import LEARNING_RATE, GRAD_CLIP, DEVICE


class OnlineTrainer:
    def __init__(self):
        self.model = LSTMModel().to(DEVICE)

        self.optimizer = optim.Adam(self.model.parameters(), lr=LEARNING_RATE)
        self.criterion = nn.MSELoss()

        self.step = 0

    def train_step(self, x, y):
        self.model.train()

        x = x.to(DEVICE)
        y = y.to(DEVICE)

        pred = self.model(x)

        loss = self.criterion(pred, y)

        self.optimizer.zero_grad()
        loss.backward()

        # Gradient clipping (VERY IMPORTANT)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), GRAD_CLIP)

        self.optimizer.step()

        return loss.item(), pred.detach().cpu().numpy()

    def predict(self, x):
        self.model.eval()

        with torch.no_grad():
            pred = self.model(x.to(DEVICE))

        return pred.cpu().numpy()
