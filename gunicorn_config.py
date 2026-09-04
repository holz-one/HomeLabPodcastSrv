# gunicorn_config.py
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
timeout = 30
# Optional: Redirect logs
accesslog = "./logs/access.log"
errorlog = "./logs/error.log"
loglevel = "info"