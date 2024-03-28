# Development

## Install by Source

Step 1: Base environment

```
mamba install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
mamba install cuda -c nvidia/label/cuda-12.1.0
```

Step 2: NVComp and Libkvikio

```
git clone git@github.com:rapidsai/kvikio.git
cd kvikio && git checkout branch-23.04
./build.sh kvikio
```
