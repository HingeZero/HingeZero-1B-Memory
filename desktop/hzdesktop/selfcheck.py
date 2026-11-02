"""Runtime environment self-check. Does not send any information externally."""
import importlib
import os
import socket
import sys
from hzdesktop import __version__
from hzdesktop.retrieval import phi


def main():
    print('HingeZero Memory Desktop ' + __version__)
    for package in ('cryptography', 'pypdf', 'tkinter'):
        try:
            importlib.import_module(package)
            print(f'[PASS] {package} available')
        except Exception as e:
            print(f'[FAIL] {package}: {e}')
            return 1
    assert phi(0.0) == 0.0
    print('[PASS] HingeZero operator self-check')
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        print('[PASS] IPv4 loopback available')
    print('[INFO] Ollama/API are not started by this check')
    print('[INFO] No security audit can guarantee absence of vulnerabilities')
    return 0


if __name__ == '__main__':
    sys.exit(main())
