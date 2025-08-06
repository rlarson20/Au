import httpx

models_dev = "https://models.dev/api.json"
mdev_list = httpx.get(models_dev).json()
