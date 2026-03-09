# 这个脚本用于测试当前环境中安装的onnxruntime和torch的版本，以及onnxruntime可用的providers和torch的cudnn版本。它可以帮助我们确认是否正确安装了这些库，并且它们是否能够正常工作。

import onnxruntime as ort
print("onnxruntime:", ort.__version__)
print("providers:", ort.get_available_providers())
import torch
print(torch.backends.cudnn.version())