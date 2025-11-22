# Install ComfyUI on your Network Volume

1. [Create a RunPod Account](https://runpod.io).
2. Create a [RunPod Network Volume](https://www.runpod.io/console/user/storage).
3. Attach the Network Volume to a Secure Cloud [GPU pod](https://www.runpod.io/console/gpu-secure-cloud).
4. Select the RunPod Pytorch 2 template.
5. Deploy the GPU Cloud pod.
6. Once the pod is up, open a Terminal and install the required dependencies.

## Installation

1. Install the ComfyUI:
```bash
# Clone the repo
cd /workspace
git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git comfywan

# Upgrade Python
apt update
apt -y upgrade
apt-get install aria2 # for downloading models

# Ensure Python version is 3.10.12
python -V

# Create and activate venv
cd comfywan
python -m venv /workspace/venv
source /workspace/venv/bin/activate

# Install Torch 
pip install --no-cache-dir torch==2.7.0+cu128 --index-url https://download.pytorch.org/whl/cu128 --no-deps
# pip install --no-cache-dir torchvision==0.22.0+cu128 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128
pip install torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0 --extra-index-url https://download.pytorch.org/whl/cu128

# Install ComfyUI
pip install -r requirements.txt

# Installing ComfyUI Manager
git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager
pip install -r custom_nodes/ComfyUI-Manager/requirements.txt

# Installing KJNodes
git clone https://github.com/kijai/ComfyUI-KJNodes.git custom_nodes/ComfyUI-KJNodes
pip install -r custom_nodes/ComfyUI-KJNodes/requirements.txt

# install ComfyUI-GGUF
git clone https://github.com/city96/ComfyUI-GGUF custom_nodes/ComfyUI-GGUF
pip install -r custom_nodes/ComfyUI-GGUF/requirements.txt

# rgthree nodes
git clone https://github.com/rgthree/rgthree-comfy.git custom_nodes/rgthree-comfy

# Install Rife interpolation
git clone https://github.com/yuvraj108c/ComfyUI-Rife-Tensorrt custom_nodes/ComfyUI-Rife-Tensorrt
pip install -r custom_nodes/ComfyUI-Rife-Tensorrt/requirements.txt

# WAN video wrapper
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper custom_nodes/ComfyUI-WanVideoWrapper
pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt

git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite custom_nodes/ComfyUI-VideoHelperSuite
pip install -r custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt

# required for WAN animate
git clone https://github.com/kijai/ComfyUI-WanAnimatePreprocess custom_nodes/ComfyUI-WanAnimatePreprocess
pip install -r custom_nodes/ComfyUI-WanAnimatePreprocess/requirements.txt
    
git clone https://github.com/kijai/ComfyUI-segment-anything-2 custom_nodes/ComfyUI-segment-anything-2
```
2. Install the Serverless dependencies:
```bash
pip install requests runpod==1.7.9 websocket-client
pip install onnxruntime-gpu
pip install triton
pip install mutagen

# Install SageAttention after ensuring the correct torch version
# wget -O https://github.com/atumn/runpod-wan/raw/refs/heads/main/sageattention-2.1.1-cp310-cp310-linux_x86_64.whl
# RUN pip install /tmp/sageattention-2.1.1-cp310-cp310-linux_x86_64.whl
git clone https://github.com/thu-ml/SageAttention.git
cd SageAttention 
pip install --no-build-isolation --no-cache-dir --force-reinstall --compile .

```
3. Download models:
```bash
# WAN2.2 I2V Q5_M
aria2c -x16 -s16 -d /workspace/models/diffusion_models -o wan2.2_i2v_high_noise_14B_Q5_K_M.gguf --continue=true https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/wan2.2_i2v_high_noise_14B_Q5_K_M.gguf
aria2c -x16 -s16 -d /workspace/models/diffusion_models -o wan2.2_i2v_low_noise_14B_Q5_K_M.gguf --continue=true https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/wan2.2_i2v_low_noise_14B_Q5_K_M.gguf

# WAN2.2 T2V Q5_M
aria2c -x16 -s16 -d /workspace/models/diffusion_models -o wan2.2_t2v_high_noise_14B_Q5_K_M.gguf --continue=true https://huggingface.co/bullerwins/Wan2.2-T2V-A14B-GGUF/resolve/main/wan2.2_t2v_high_noise_14B_Q5_K_M.gguf
aria2c -x16 -s16 -d /workspace/models/diffusion_models -o wan2.2_t2v_low_noise_14B_Q5_K_M.gguf --continue=true https://huggingface.co/bullerwins/Wan2.2-T2V-A14B-GGUF/resolve/main/wan2.2_t2v_low_noise_14B_Q5_K_M.gguf

# Download text encoders also GGUF
aria2c -x16 -s16 -d /workspace/models/text_encoders -o umt5_xxl_fp8_e4m3fn_scaled.safetensors --continue=true https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors

# Create CLIP vision directory and download models
aria2c -x16 -s16 -d /workspace/models/clip_vision -o clip_vision_h.safetensors --continue=true https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors

# Download VAE
aria2c -x16 -s16 -d /workspace/models/vae -o wan_2.1_vae.safetensors --continue=true https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors

# see loras.md for LORAs

# WAN2.2-Animate
aria2c -x16 -s16 -d /workspace/models/vae -o Wan2_1_VAE_bf16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors
# aria2c -x16 -s16 -d /workspace/models/clip_vision -o clip_vision_h.safetensors --continue=true https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors
aria2c -x16 -s16 -d /workspace/models/text_encoders -o umt5-xxl-enc-bf16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors
aria2c -x16 -s16 -d /workspace/models/loras -o WanAnimate_relight_lora_fp16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_relight/WanAnimate_relight_lora_fp16.safetensors
aria2c -x16 -s16 -d /workspace/models/loras -o lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors
aria2c -x16 -s16 -d /workspace/models/diffusion_models -o Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/Wan22Animate/Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors

aria2c -x16 -s16 -d /workspace/models/diffusion_models -o Wan2_2-Animate-14B_fp8_scaled_e5m2_KJ_v2.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/Wan22Animate/Wan2_2-Animate-14B_fp8_scaled_e5m2_KJ_v2.safetensors

# detection
aria2c -x16 -s16 -d /workspace/models/detection -o yolov10m.onnx --continue=true https://huggingface.co/Wan-AI/Wan2.2-Animate-14B/resolve/main/process_checkpoint/det/yolov10m.onnx
aria2c -x16 -s16 -d /workspace/models/detection -o vitpose_h_wholebody_model.onnx --continue=true https://huggingface.co/Kijai/vitpose_comfy/resolve/main/onnx/vitpose_h_wholebody_model.onnx
aria2c -x16 -s16 -d /workspace/models/detection -o vitpose_h_wholebody_data.bin --continue=true https://huggingface.co/Kijai/vitpose_comfy/resolve/main/onnx/vitpose_h_wholebody_data.bin
```

4. Create extra_model_paths.yaml file:
```bash
touch /workspace/comfywan/extra_model_paths.yaml
# contents in the file at root path of this repo
```