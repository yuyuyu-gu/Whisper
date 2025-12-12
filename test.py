import onnxruntime as ort
print("onnxruntime:", ort.__version__)
print("providers:", ort.get_available_providers())
import torch
print(torch.backends.cudnn.version())