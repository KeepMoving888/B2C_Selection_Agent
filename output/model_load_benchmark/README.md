# vLLM AWQ Model Load Time Benchmark

## Measured Results

| Storage Location | Load Time |
|------------------|-----------|
| WSL ext4 (`/home/b2cuser/models`) | 32.10 s |
| E: drive (`/mnt/e/models`) | 140.00 s |

**E: drive is 4.4x slower** than WSL ext4 for model loading.

## Why?

WSL2 accesses Windows drives (`/mnt/e`, `/mnt/c`, etc.) via the 9P network protocol, not native block IO.
Even on a fast SSD, 9P adds protocol overhead and does not provide the same sequential-read throughput as
WSL's own ext4 virtual disk. For multi-GB safetensors files, this results in significantly longer load times.

## Recommendation

For production serving, keep the active model on WSL ext4 (`/home/b2cuser/models`) and use E: drive only
for backups or archives. If you must use E: drive, expect ~2-3 minute cold-start load times for a 5GB AWQ model
(and proportionally longer for a 14GB FP16 model).
