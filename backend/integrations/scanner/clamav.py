"""Protocolo ClamAV INSTREAM; somente resposta explícita OK libera o arquivo."""
import socket
import struct
import time

from django.conf import settings


def scan(source):
    deadline = time.monotonic() + settings.DOCUMENT_SCANNER_TIMEOUT
    with socket.create_connection((settings.DOCUMENT_SCANNER_HOST, settings.DOCUMENT_SCANNER_PORT),
                                  timeout=settings.DOCUMENT_SCANNER_TIMEOUT) as client:
        def remaining():
            seconds = deadline - time.monotonic()
            if seconds <= 0:
                raise TimeoutError("Scanner deadline exceeded")
            client.settimeout(seconds)

        remaining()
        client.sendall(b"zINSTREAM\x00")
        total = 0
        while chunk := source.read(65536):
            total += len(chunk)
            if total > 20 * 1024 * 1024:
                raise ValueError("Scanner size limit")
            remaining()
            client.sendall(struct.pack("!I", len(chunk)) + chunk)
        remaining()
        client.sendall(struct.pack("!I", 0))
        response = b""
        while b"\x00" not in response and len(response) < 4096:
            remaining()
            chunk = client.recv(1024)
            if not chunk:
                break
            response += chunk
        if response == b"stream: OK\x00":
            return True
        if response.startswith(b"stream: ") and response.endswith(b" FOUND\x00"):
            return False
        raise RuntimeError("Scanner did not confirm a verdict")
