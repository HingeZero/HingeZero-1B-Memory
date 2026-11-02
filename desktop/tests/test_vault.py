import sqlite3
import pytest
from hzdesktop.vault import Vault

PASSWORD = 'this-is-a-long-test-passphrase'


def test_encryption_and_persistence(tmp_path):
    path = tmp_path / 'vault' / 'data.sqlite3'
    with Vault(path, PASSWORD, create=True) as vault:
        identifier = vault.add('Private Title', 'my secret appointment is on Tuesday', 'test')
        assert vault.count() == 1
        vault.backup_encrypted(tmp_path / 'backup.sqlite3')
        raw = path.read_bytes()
        assert b'Private Title' not in raw
        assert b'my secret appointment' not in raw
        assert vault.list()[0]['id'] == identifier
    with pytest.raises(ValueError):
        Vault(path, 'wrong-password')
    with Vault(path, PASSWORD) as reopened:
        assert reopened.list()[0]['content'] == 'my secret appointment is on Tuesday'
        reopened.delete(identifier)
        assert reopened.count() == 0
    with Vault(tmp_path / 'backup.sqlite3', PASSWORD) as backup:
        assert backup.count() == 1


def test_no_accidental_overwrite(tmp_path):
    path = tmp_path / 'vault.db'
    with Vault(path, PASSWORD, create=True):
        pass
    with pytest.raises(FileExistsError):
        Vault(path, PASSWORD, create=True)
    with pytest.raises(ValueError):
        Vault(tmp_path / 'short.db', 'short', create=True)
