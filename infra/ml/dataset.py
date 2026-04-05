import torch
import numpy as np

# -------------------------------
# NORMALIZATION CONSTANTS
# -------------------------------

CPU_SCALE = 1.0              # CPU already small
MEMORY_SCALE = 1e8          # Normalize memory (~100MB scale)
DEMAND_SCALE = 1e8          # Same for demand


def normalize(sequence):
    seq = sequence.copy()

    # request_rate (leave)
    # cpu_usage (leave)

    # memory_usage
    seq[:, 2] = seq[:, 2] / MEMORY_SCALE

    # cpu_demand (leave small)

    # memory_demand
    seq[:, 4] = seq[:, 4] / DEMAND_SCALE

    return seq


def build_sample(sequence):
    """
    Input: (10, 6)
    """

    sequence = normalize(sequence)

    x = sequence[:-1]   # (9, 6)
    y = sequence[-1]

    target = y[1:3]     # cpu_usage, memory_usage (normalized)

    x = torch.tensor(x, dtype=torch.float32).unsqueeze(0)
    target = torch.tensor(target, dtype=torch.float32).unsqueeze(0)

    return x, target
