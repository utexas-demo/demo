# Jetson Thor Deployment Guide

**Related ADR:** [ADR-0007: Jetson Thor Edge Deployment](../architecture/0007-jetson-thor-edge-deployment.md)

---

## Prerequisites

- NVIDIA Jetson Thor T5000 development kit
- JetPack 7.x installed (includes Ubuntu 24.04, CUDA 13, TensorRT 10.13)
- NVMe SSD with ≥256 GB free space
- Wi-Fi 7 access point on the local network
- Docker + NVIDIA Container Toolkit installed

## Jetson Setup

### 1. Flash JetPack

Follow NVIDIA's official guide to flash JetPack 7.x onto the Jetson Thor:

```bash
# On host machine (x86_64 Ubuntu)
sudo apt install nvidia-jetpack-flash
# Follow NVIDIA SDK Manager prompts
```

### 2. Install Docker + NVIDIA Container Toolkit

JetPack 7.x includes Docker by default. Verify and install the NVIDIA Container Toolkit:

```bash
# Verify Docker
docker --version

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU access in containers
docker run --rm --gpus all nvcr.io/nvidia/pytorch:25.08-py3 nvidia-smi
```

### 3. Clone and Deploy

```bash
git clone <pms-backend-repo-url> /opt/pms/backend
cd /opt/pms/backend

# Copy and configure environment
cp .env.example .env
# Edit .env with production values:
#   DATABASE_URL=postgresql+asyncpg://postgres:<password>@postgres:5432/pms
#   SECRET_KEY=<random-secret>
#   ENCRYPTION_KEY=<random-key>
#   FEATURE_SUB_PR_0009_WOUND_ASSESSMENT=true  (when models are ready)
#   FEATURE_SUB_PR_0010_PATIENT_ID_VERIFY=true  (when models are ready)
#   FEATURE_SUB_PR_0011_DOCUMENT_OCR=true       (when models are ready)

# Build and start
docker compose up -d --build
```

## Docker Compose Overview

The `docker-compose.yml` in `pms-backend` defines three services:

| Service | Image | Port | GPU | Purpose |
|---|---|---|---|---|
| `backend` | `Dockerfile.jetson` | 8000 | Yes (all) | FastAPI + vision inference |
| `frontend` | `node:24-alpine` | 3000 | No | Next.js web UI |
| `postgres` | `postgres:16` | 5432 | No | Database with persistent volume |

### GPU Access

The backend service requests GPU access via Docker Compose deploy config:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

## Wi-Fi 7 Network Configuration

### Jetson Network Setup

```bash
# Connect Jetson to Wi-Fi 7 AP
nmcli device wifi connect "<SSID>" password "<password>"

# Assign static IP (recommended for stable Android client connections)
nmcli connection modify "<SSID>" \
  ipv4.method manual \
  ipv4.addresses 192.168.1.100/24 \
  ipv4.gateway 192.168.1.1 \
  ipv4.dns 192.168.1.1
nmcli connection up "<SSID>"
```

### Android Client Configuration

In the Android app's build config or runtime settings, set the API base URL to the Jetson's IP:

```
API_BASE_URL=http://192.168.1.100:8000
```

The frontend web UI is accessible at `http://192.168.1.100:3000`.

### Firewall Rules

```bash
# Allow backend, frontend, and PostgreSQL (local only)
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp
# Do NOT expose port 5432 externally — PostgreSQL is internal only
```

## GPU Resource Allocation

With 128 GB unified memory and 2560 Blackwell GPU cores, recommended allocation:

| Workload | GPU Memory | Notes |
|---|---|---|
| MONAI wound assessment | ~2 GB | Segmentation model + TensorRT engine |
| ArcFace patient ID | ~500 MB | Embedding model + TensorRT engine |
| PaddleOCR | ~1 GB | Detection + recognition models |
| PyTorch runtime | ~2 GB | CUDA context + overhead |
| PostgreSQL + backend | CPU only | No GPU usage |
| **Total GPU** | **~5.5 GB** | Well within 128 GB unified memory |

## Health Checks

```bash
# Verify all services are running
docker compose ps

# Check backend health
curl http://localhost:8000/health

# Check GPU availability inside backend container
docker compose exec backend nvidia-smi

# View logs
docker compose logs -f backend
```

## Troubleshooting

| Issue | Solution |
|---|---|
| `nvidia-smi` not found in container | Verify NVIDIA Container Toolkit is installed and Docker runtime is configured |
| CUDA out of memory | Check `nvidia-smi` for other processes using GPU memory |
| Android can't connect | Verify Jetson IP is reachable, firewall ports 8000/3000 are open |
| Database connection refused | Check `docker compose ps` — postgres may still be starting |
| TensorRT engine build fails | Ensure JetPack version matches the CUDA/TensorRT versions in Dockerfile |
