"""Only a trusted local TLS proxy may reach this listener. Python 3.12+ required."""

bind = "127.0.0.1:8765"
workers = 2
worker_class = "sync"
timeout = 30
graceful_timeout = 30
limit_request_line = 4094
limit_request_fields = 30
limit_request_field_size = 16384
forwarded_allow_ips = "127.0.0.1,::1"
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
accesslog = None
errorlog = "-"
capture_output = False
umask = 0o077
