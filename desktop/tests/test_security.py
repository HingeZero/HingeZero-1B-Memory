"""Regression tests for permission and untrusted-import boundaries."""
import os
import stat
from zipfile import ZipFile

import pytest
from hzdesktop.vault import Vault
from hzdesktop.importers import extract


def test_backup_preserves_user_directory_permissions(tmp_path):
    directory = tmp_path / 'my-shared-backups'
    directory.mkdir(mode=0o755)
    if os.name == 'posix':
        # This *test fixture* deliberately simulates an existing shared directory.
        # The encrypted backup must stay 0600 and must never chmod this parent.
        # codeql[py/overly-permissive-file]
        os.chmod(directory, 0o755)
    with Vault(tmp_path / 'appvault' / 'vault.sqlite3', 'long-and-unique-passphrase', create=True) as vault:
        vault.add('test', 'secret memory')
        dest = directory / 'backup.sqlite3'
        vault.backup_encrypted(dest)
    if os.name == 'posix':
        assert stat.S_IMODE(directory.stat().st_mode) == 0o755
        assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    with Vault(dest, 'long-and-unique-passphrase') as backup:
        assert backup.list()[0]['content'] == 'secret memory'


def test_backup_will_not_overwrite_or_follow_symlink(tmp_path):
    with Vault(tmp_path / 'vault.sqlite3', 'long-and-unique-passphrase', create=True) as vault:
        existing = tmp_path / 'existing.db'
        existing.write_bytes(b'untouched')
        with pytest.raises(FileExistsError):
            vault.backup_encrypted(existing)
        assert existing.read_bytes() == b'untouched'
        alias = tmp_path / 'alias.db'
        try:
            alias.symlink_to(existing)
        except (OSError, NotImplementedError):
            pytest.skip('symlinks unavailable')
        with pytest.raises((FileExistsError, ValueError)):
            vault.backup_encrypted(alias)
        assert existing.read_bytes() == b'untouched'


def test_docx_rejects_entity_expansion(tmp_path):
    payload = '<?xml version="1.0"?><!DOCTYPE w:document [<!ENTITY x "EXPLOITED">]><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:t>&x;</w:t></w:p></w:document>'
    doc = tmp_path / 'evil.docx'
    with ZipFile(doc, 'w') as zipped:
        zipped.writestr('word/document.xml', payload)
    with pytest.raises(Exception):
        extract(doc)


def test_backup_refuses_dangling_symlink_destination(tmp_path):
    alias = tmp_path / 'backup-alias.db'
    target = tmp_path / 'not-created.db'
    try:
        alias.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip('symlinks unavailable')
    with Vault(tmp_path / 'source' / 'vault.sqlite3', 'long-and-unique-passphrase', create=True) as vault:
        vault.add('meeting', 'private content')
        with pytest.raises((FileExistsError, ValueError, OSError)):
            vault.backup_encrypted(alias)
    assert alias.is_symlink()
    assert not target.exists()
