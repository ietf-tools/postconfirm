"""
Runs postconfirm.py as a real process and checks how it handles SIGTERM.

In Kubernetes the milter is PID 1, where an unhandled SIGTERM is ignored and
the pod is SIGKILLed at the end of the grace period, cutting off whatever
milter sessions are in flight.
"""
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_listener(proc: subprocess.Popen, port: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"postconfirm exited early:\n{proc.stdout.read()}")
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.05)
    pytest.fail("postconfirm did not start listening")


@pytest.fixture
def start_postconfirm(tmp_path):
    processes = []

    def start(drain_seconds: float = 10):
        port = _free_port()
        key_file = tmp_path / "key"
        key_file.write_bytes(b"test-secret-key")
        config_file = tmp_path / "postconfirm.cfg"
        config_file.write_text(
            f"key_file: '{key_file}'\n"
            f"log: {{ filename: '{tmp_path / 'postconfirm.log'}' }}\n"
            f"shutdown: {{ drain_seconds: {drain_seconds} }}\n"
            f"milter_port: {port}\n"
            "db: {}\n"
        )

        proc = subprocess.Popen(
            [sys.executable, "postconfirm.py", "-c", str(config_file)],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append(proc)
        _wait_for_listener(proc, port)

        return proc, port

    yield start

    for proc in processes:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        proc.stdout.close()


def _open_session(port: int) -> socket.socket:
    session = socket.create_connection(("127.0.0.1", port))
    time.sleep(0.2)  # let the server accept it
    return session


class TestShutdown:
    def test_exits_cleanly_on_sigterm(self, start_postconfirm):
        proc, _ = start_postconfirm()

        proc.send_signal(signal.SIGTERM)

        assert proc.wait(timeout=5) == 0

    def test_waits_for_in_flight_sessions(self, start_postconfirm):
        proc, port = start_postconfirm()
        session = _open_session(port)

        proc.send_signal(signal.SIGTERM)
        time.sleep(0.5)
        assert proc.poll() is None

        session.close()
        assert proc.wait(timeout=5) == 0

    def test_stops_accepting_connections_on_sigterm(self, start_postconfirm):
        proc, port = start_postconfirm()
        session = _open_session(port)

        proc.send_signal(signal.SIGTERM)
        time.sleep(0.5)
        assert proc.poll() is None

        with pytest.raises(ConnectionRefusedError):
            socket.create_connection(("127.0.0.1", port), timeout=1)
        session.close()

    def test_gives_up_on_sessions_after_the_drain_deadline(self, start_postconfirm):
        proc, port = start_postconfirm(drain_seconds=1)
        session = _open_session(port)

        signalled_at = time.monotonic()
        proc.send_signal(signal.SIGTERM)

        assert proc.wait(timeout=10) == 0
        assert time.monotonic() - signalled_at >= 0.9
        session.close()
