"""Minimal Gradio web launcher for end-to-end testing."""
import os, sys, threading, time, socket

# Ensure src/ is on the path so canada_id resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Best-effort .env loading
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from canada_id.web import create_app

PORT = 7865

def _find_free_port() -> int:
    for p in range(PORT, PORT + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return PORT

if __name__ == "__main__":
    port = _find_free_port()
    app = create_app()
    print(f"Launching Gradio on http://127.0.0.1:{port}")
    app.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        show_error=True,
    )
