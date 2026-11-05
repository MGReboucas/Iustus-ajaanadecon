"""Run the web server and optionally mail delivery in the same instance."""
import os
import signal
import subprocess
import sys
import time


def main():
    children = []
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        children.append(subprocess.Popen([
            "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:" + os.environ.get("PORT", "8000"),
            "--workers", "2", "--threads", "2", "--timeout", "60", "--error-logfile", "-",
        ]))
        if os.environ.get("MAIL_WORKER_IN_WEB", "false").lower() == "true":
            children.append(subprocess.Popen([sys.executable, "manage.py", "run_mail_queue"]))
        while not stopping:
            if any(child.poll() is not None for child in children):
                # A dead mail process must not leave a healthy-looking web-only service.
                return 1
            time.sleep(1)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        deadline = time.monotonic() + 25
        for child in children:
            try:
                child.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    sys.exit(main())
