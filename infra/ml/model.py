import torch
import torch.nn as nn

from ml.config import INPUT_SIZE, HIDDEN_SIZE, NUM_LAYERS, OUTPUT_SIZE


class LSTMModel(nn.Module):
    def __init__(self):
        super(LSTMModel, self).__init__()

        self.lstm = nn.LSTM(
            input_size=INPUT_SIZE,
            hidden_size=HIDDEN_SIZE,
            num_layers=NUM_LAYERS,
            batch_first=True
        )

        self.fc = nn.Linear(HIDDEN_SIZE, OUTPUT_SIZE)

    def forward(self, x):
        """
        x shape: (batch_size, seq_len=10, input_size=6)
        """

        out, _ = self.lstm(x)

        # Take last timestep
        last_out = out[:, -1, :]

        out = self.fc(last_out)

        return out
