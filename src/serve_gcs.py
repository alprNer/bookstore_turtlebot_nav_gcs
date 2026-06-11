#!/usr/bin/env python3
"""
GCS için basit HTTP sunucusu.
Çalıştırma: python3 serve.py   (varsayılan port: 8888)
Tarayıcıda aç: http://localhost:8888
"""
import http.server
import os
import sys

# ROS __name:=... gibi argümanları filtrele, sadece sayısal olanı al
_user_args = [a for a in sys.argv[1:] if not a.startswith('_')]
PORT = int(_user_args[0]) if _user_args else 8888

# gcs/ dizini: bu dosya src/ içinde, html src/ ile kardeş gcs/ içinde
DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gcs")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def log_message(self, fmt, *args):
        pass  # sessiz mod

if __name__ == "__main__":
    with http.server.HTTPServer(("", PORT), Handler) as srv:
        print(f"GCS sunucusu başlatıldı: http://localhost:{PORT}")
        print("Durdurmak için Ctrl+C")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nSunucu durduruldu.")
