"""Desktop launcher for moviepropIDgen.

Opens the Gradio app in a native Windows window using pywebview.
No browser needed — runs as a standalone desktop application.
"""
import threading
import time
import socket

import webview

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None

from canada_id.web import create_app

PORT = 7865


def _find_free_port() -> int:
    """Find a free port starting from PORT."""
    for p in range(PORT, PORT + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return PORT


def _run_gradio(port: int):
    """Start the Gradio server in a background thread."""
    app = create_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        prevent_thread_lock=True,
        show_error=True,
    )


def main():
    """Launch the desktop application."""
    if load_dotenv is not None:
        load_dotenv()

    port = _find_free_port()

    server_thread = threading.Thread(
        target=_run_gradio, args=(port,), daemon=True,
    )
    server_thread.start()

    # Wait for server to be ready
    for _ in range(30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.5)

    webview.create_window(
        "moviepropIDgen",
        f"http://127.0.0.1:{port}",
        width=1200,
        height=800,
        min_size=(900, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
