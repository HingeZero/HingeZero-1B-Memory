import pytest
from zipfile import ZipFile
from hzdesktop.importers import extract, chunks


def test_import_text_and_word(tmp_path):
    document = tmp_path / 'text.md'
    document.write_text('This appointment happened at midnight', encoding='utf-8')
    assert 'midnight' in extract(document)
    word = tmp_path / 'word.docx'
    xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Private note</w:t></w:r></w:p></w:body></w:document>'
    with ZipFile(word,'w') as z:
        z.writestr('word/document.xml',xml)
    assert 'Private note' in extract(word)
    assert len(chunks('a' * 2400)) == 3


def test_import_rejects_unselected_formats_and_large_files(tmp_path):
    executable = tmp_path / 'malicious.sh'
    executable.write_text('echo hello')
    with pytest.raises(ValueError):
        extract(executable)
    huge = tmp_path / 'huge.txt'
    huge.write_bytes(b'a' * (8 * 1024 * 1024 + 1))
    with pytest.raises(ValueError):
        extract(huge)
