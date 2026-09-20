import socket

from utils.network_utils import get_local_ip, test_network_connectivity as network_connectivity
from utils.qr_generator import build_and_display_qr_ascii, generate_qr_code


def test_get_local_ip_uses_udp_socket(monkeypatch):
    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def connect(self, address):
            assert address == ("8.8.8.8", 80)

        def getsockname(self):
            return ("192.168.1.44", 1234)

    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: FakeSocket())

    assert get_local_ip() == "192.168.1.44"


def test_get_local_ip_falls_back_when_network_fails(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(socket, "socket", fail)

    assert get_local_ip() == "127.0.0.1"


def test_network_connectivity_returns_true(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(socket, "create_connection", lambda address, timeout: FakeConnection())

    assert network_connectivity("127.0.0.1", 5000, 0.1)


def test_network_connectivity_returns_false_on_socket_error(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.timeout("timed out")

    monkeypatch.setattr(socket, "create_connection", fail)

    assert not network_connectivity("127.0.0.1", 5000)


def test_generate_qr_code_writes_png(tmp_path, monkeypatch):
    displayed = []
    monkeypatch.setattr("utils.qr_generator.display_qr_ascii", displayed.append)
    output_path = tmp_path / "nested" / "pair.png"

    generate_qr_code("https://example.test", str(output_path), size=2)

    assert output_path.exists()
    assert displayed == ["https://example.test"]


def test_generate_qr_code_rejects_invalid_input(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        generate_qr_code("", str(tmp_path / "pair.png"))


def test_display_qr_ascii_prints_url(capsys):
    display_qr_ascii("https://example.test")

    assert "URL: https://example.test" in capsys.readouterr().out
