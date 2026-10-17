"""Verify the uploaded research package, then restore compressed legacy CSV inputs."""
from pathlib import Path
import gzip,hashlib,json
P=Path(__file__).resolve().parent
manifest=json.loads((P/'PUBLISH_MANIFEST.json').read_text())
for item in manifest['study_files']:
    f=P/item['path']
    assert f.is_file(),str(f)
    assert hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256'],str(f)
for item in manifest['compressed_inputs']:
    original=P/item['original_path'];packed=P/item['path']
    data=gzip.decompress(packed.read_bytes())
    assert hashlib.sha256(data).hexdigest()==item['original_sha256']
    if original.exists():
        assert hashlib.sha256(original.read_bytes()).hexdigest()==item['original_sha256'],str(original)
    else:
        original.write_bytes(data)
    print('Verified/restored:',original.relative_to(P))
print('All uploaded study files verified; input CSV files ready.')
