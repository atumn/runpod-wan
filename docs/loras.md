## Downloading loras:

note: if civitai requires token, set it like so:
```bash
token=YOUR_TOKEN
```
LORAs:
```bash
# WAN22 lightx2v high for I2V
aria2c -x16 -s16 -d /workspace/models/loras -o Wan2.2-Lightning_I2V-A14B-4steps-lora_HIGH_fp16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan22-Lightning/Wan2.2-Lightning_I2V-A14B-4steps-lora_HIGH_fp16.safetensors
# WAN22 lightx2v low for I2V
aria2c -x16 -s16 -d /workspace/models/loras -o Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan22-Lightning/Wan2.2-Lightning_I2V-A14B-4steps-lora_LOW_fp16.safetensors

# WAN22 lightx2v update 10/30 for HIGH only
aria2c -x16 -s16 -d /workspace/models/loras -o Wan_2_2_I2V_A14B_HIGH_lightx2v_MoE_distill_lora_rank_64_bf16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_Lightx2v/Wan_2_2_I2V_A14B_HIGH_lightx2v_MoE_distill_lora_rank_64_bf16.safetensors
aria2c -x16 -s16 -d /workspace/models/loras -o Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_v1030_rank_64_bf16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan22_Lightx2v/Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_v1030_rank_64_bf16.safetensors

# WAN22 lightx2v high for T2V
aria2c -x16 -s16 -d /workspace/models/loras -o Wan2.2-Lightning_T2V-v1.1-A14B-4steps-lora_HIGH_fp16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan22-Lightning/Wan2.2-Lightning_T2V-v1.1-A14B-4steps-lora_HIGH_fp16.safetensors
# WAN22 lightx2v low for T2V
aria2c -x16 -s16 -d /workspace/models/loras -o Wan2.2-Lightning_T2V-v1.1-A14B-4steps-lora_LOW_fp16.safetensors --continue=true https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan22-Lightning/Wan2.2-Lightning_T2V-v1.1-A14B-4steps-lora_LOW_fp16.safetensors

# phut hon dance
aria2c -x16 -s16 -d /workspace/models/loras -o dbc.safetensors --continue=true "https://civitai.com/api/download/models/1542806?type=Model&format=SafeTensor&token=${token}"
# trigger words: 
# dabaichui
# making dabaichui motion
# example: dabaichui，the subject holds their head with both hands and twists their waist and hips left and right ，making dabaichui motion

# WAN missionary
aria2c -x16 -s16 -d /workspace/models/loras -o wan2.2_i2v_highnoise_pov_missionary_v1.0.safetensors --continue=true "https://civitai.com/api/download/models/2098405?type=Model&format=SafeTensor&token=${token}"
aria2c -x16 -s16 -d /workspace/models/loras -o wan2.2_i2v_lownoise_pov_missionary_v1.0.safetensors --continue=true "https://civitai.com/api/download/models/2098396?type=Model&format=SafeTensor&token=${token}"
# Important parts of the prompt:
# with her legs spread having sex with a man
# ...
# A man is thrusting his penis back and forth inside her vagina at the bottom of the screen
# {Movement is fast with bouncing breasts|Movement is slow}
# Her breasts are {small|medium sized|large}

# WAN 2.2 sigma face
aria2c -x16 -s16 -d /workspace/models/loras -o wan2_2_14b_i2v_sigma_000002100_high_noise.safetensors --continue=true "https://civitai.com/api/download/models/2147746?type=Model&format=SafeTensor&token=${token}"

aria2c -x16 -s16 -d /workspace/models/loras -o wan2_2_14b_i2v_sigma_000002100_low_noise.safetensors --continue=true "https://civitai.com/api/download/models/2147745?type=Model&format=SafeTensor&token=${token}"
# trigger words:
# Subject is doing sigma face expression

# CheekPinch Pals LORA V1.0
aria2c -x16 -s16 -d /workspace/models/loras -o cheekpinch_pals_v1.safetensors --continue=true "https://civitai.green/api/download/models/2159837?type=Model&format=SafeTensor&token=${token}"
# trigger words:
# HUPONNL，画面里女人的脸颊被双手手指轻柔拉扯，她的面部表情随动作从平静逐步变为嘟嘟嘴，噘嘴或者微笑等不同状态，展现出趣味互动效果。

# WAN i2v orgasm
aria2c -x16 -s16 -d /workspace/models/loras -o wan2.2_i2v_orgasm_high_14b.safetensors --continue=true "https://civitai.com/api/download/models/2178013?type=Model&format=SafeTensor&token=${token}"

aria2c -x16 -s16 -d /workspace/models/loras -o wan2.2_i2v_orgasm_low_14b.safetensors --continue=true "https://civitai.com/api/download/models/2178018?type=Model&format=SafeTensor&token=${token}"
# trigger words:
# She is having an orgasm. Her body shudders and shivers as a profound, guttural moan of sexual pleasure escapes her lips, her face a portrait of sublime ecstasy as she reaches the peak of her orgasm.

# WAN 2.2 Oral Insertion
aria2c -x16 -s16 -d /workspace/models/loras -o wan2.2-i2v-oral-insertion-v1.0.zip --continue=true "https://civitai.com/api/download/models/2121297?type=Model&format=Diffusers&token=${token}"
# unzipped:
# wan2.2-i2v-high-oral-insertion-v1.0.safetensors
# wan2.2-i2v-low-oral-insertion-v1.0.safetensors
# trigger words:
# A man appears and she sucks his penis
```