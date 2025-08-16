bind = "0.0.0.0:$PORT"  # Render asignará el puerto dinámicamente
workers = 4
worker_class = 'gthread'
threads = 4
timeout = 120
accesslog = '-'
errorlog = '-'
