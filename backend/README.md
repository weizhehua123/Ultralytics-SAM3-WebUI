## Ultralytics SAM3 WebUI Backend

### Run (cloud)
- Activate conda env: `/mnt/cloud-disk/conda-envs/Utralytics-sam3`
- Start API (workers must be 1):
  - `uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 1`

### Env vars
- `SAM3_CHECKPOINT_PATH` default: `/mnt/cloud-disk/models/sam3/facebook/sam3/sam3.pt`
- `SAM3_VOCAB_PATH` default: `/mnt/cloud-disk/models/sam3/facebook/sam3/bpe_simple_vocab_16e6.txt.gz`
- `RESULTS_DIR` default: `/mnt/cloud-disk/sam3-webui/results`
