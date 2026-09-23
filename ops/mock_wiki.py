"""Offline manifest for the single fictional Wiki; no publishing or network I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import re

COMPANY = 'DEMO-WIKI-001'
RELATIVE_ROOT = Path('skills/team-banquet/references/mock-wiki')


def file_hashes(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('wiki directory missing or symbolic')
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('wiki symbolic link')
        if path.is_dir():
            continue
        if not path.is_file() or path.suffix not in ('.md', '.json'):
            raise ValueError('unexpected wiki file')
        relative = path.relative_to(root).as_posix()
        if relative != 'SOURCE.json':
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not {'index.md', 'metadata.json'} <= files.keys():
        raise ValueError('wiki index or metadata missing')
    return files


def manifest(root, source_commit):
    if not re.fullmatch('[0-9a-f]{40}', source_commit):
        raise ValueError('full source commit required')
    files = file_hashes(root)
    metadata = json.loads((Path(root) / 'metadata.json').read_text(encoding='utf-8'))
    if (metadata.get('company_id') != COMPANY
            or metadata.get('data_scope') != '虚构演练'
            or type(metadata.get('version')) is not int
            or metadata['version'] < 1):
        raise ValueError('invalid fictional company metadata')
    return {'company_id': COMPANY, 'knowledge_version': metadata['version'],
            'source_commit': source_commit, 'files': files}


def verify(root, source_commit, version):
    expected = manifest(root, source_commit)
    saved = json.loads((Path(root) / 'SOURCE.json').read_text(encoding='utf-8'))
    if expected['knowledge_version'] != version or saved != expected:
        raise ValueError('wiki version, file set or content differs from manifest')
    return saved


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--version', type=int, required=True)
    args = parser.parse_args()
    verified = verify(args.root, args.source_commit, args.version)
    print(json.dumps({'verified': True, 'source_commit': verified['source_commit'],
                      'knowledge_version': verified['knowledge_version'],
                      'file_count': len(verified['files'])}))
