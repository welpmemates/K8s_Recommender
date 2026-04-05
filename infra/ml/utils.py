MEMORY_SCALE = 1e8


def format_prediction(pred):
    cpu = pred[0][0]
    memory = pred[0][1] * MEMORY_SCALE  # denormalize

    return {
        "cpu_pred": float(cpu),
        "memory_pred": float(memory)
    }
