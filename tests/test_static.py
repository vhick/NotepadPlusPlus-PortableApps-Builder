import importlib.util
from pathlib import Path
import tempfile
import unittest
import hashlib
import time
import zipfile

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'npp_build.py'
spec=importlib.util.spec_from_file_location('npp_build', SCRIPT)
npp=importlib.util.module_from_spec(spec)
spec.loader.exec_module(npp)

class ResolverTests(unittest.TestCase):
    def test_numeric_sort(self):
        self.assertGreater(npp.semver('v8.9.10'),npp.semver('v8.9.9'))
        self.assertGreater(npp.semver('8.10.0'),npp.semver('8.9.99'))
        self.assertEqual(npp.package_version('8.9.9'), '8.9.9.0')
        self.assertEqual(npp.package_version('8.9.9.1'), '8.9.9.1')
    def test_prerelease_rejected(self):
        for text in ['v8.9.9-rc1', 'v8.9.9-beta', 'main', 'v8.9.9-nightly']:
            with self.assertRaises(ValueError): npp.semver(text)
    def test_official_checksum_matching(self):
        digest='a'*64
        body=f'{digest}  npp.8.9.9.portable.x64.zip\n'
        self.assertEqual(npp.parse_checksum(body.encode(),'npp.8.9.9.portable.x64.zip'),digest)
        self.assertIsNone(npp.parse_checksum(body.encode(),'npp.8.9.8.portable.x64.zip'))
    def test_nonempty_upstream_marker_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            marker = base/'App'/'doLocalConf.xml'
            marker.parent.mkdir()
            payload = b'nonempty upstream marker\n'
            marker.write_bytes(payload)
            source = base/'Other'/'Source'
            info = npp.normalize_portable_marker(marker, source)
            self.assertEqual(marker.read_bytes(), b'')
            self.assertEqual((source/'upstream-doLocalConf.xml.original').read_bytes(), payload)
            self.assertEqual(info['status'], 'normalized-to-empty')
            self.assertEqual(info['source_size'], len(payload))
            self.assertEqual(info['source_sha256'], hashlib.sha256(payload).hexdigest())

    def test_empty_or_missing_upstream_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            marker = base/'doLocalConf.xml'
            source = base/'Source'
            self.assertEqual(npp.normalize_portable_marker(marker, source)['status'], 'created-empty-marker')
            self.assertEqual(npp.normalize_portable_marker(marker, source)['status'], 'preserved-empty-marker')
            self.assertEqual(marker.stat().st_size, 0)
            self.assertFalse(source.exists())

    def test_offline_staging_pipeline_nonempty_marker(self):
        """Regression for b1r2 WinError 183: normalization creates Other/Source first.

        Exercises the real stage/ZIP/PROVENANCE/validation pipeline, with only
        the network request, Windows PE inputs and icon extractor substituted
        by controlled fixtures; it is NOT a Windows runtime test.
        """
        from types import SimpleNamespace
        from unittest.mock import patch
        import json
        import struct

        def dummy_x64_pe():
            raw = bytearray(128)
            raw[0:2] = b'MZ'
            struct.pack_into('<I', raw, 60, 64)
            raw[64:68] = b'PE\0\0'
            struct.pack_into('<H', raw, 68, 0x8664)
            return bytes(raw)

        def controlled_icons(_exe, appinfo):
            # Only mock unavailable Windows resource extraction. ZIP checks
            # remain real; images are fixtures, not distributable outputs.
            (appinfo/'appicon.ico').write_bytes(b'\0\0\1\0fixture')
            png = b'\x89PNG\r\n\x1a\nfixture'
            (appinfo/'appicon_16.png').write_bytes(png)
            (appinfo/'appicon_32.png').write_bytes(png)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            work = base/'build'
            work.mkdir()
            version = '8.9.9'
            asset = f'npp.{version}.portable.x64.zip'
            archive = work/asset
            payload = b'upstream marker with nonzero bytes'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('notepad++.exe', dummy_x64_pe())
                z.writestr('doLocalConf.xml', payload)
                z.writestr('plugins/config/empty/', b'')
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            checksums = f'{digest}  {asset}\n'.encode('ascii')
            launcher = base/'NotepadPlusPlusPortable.exe'
            launcher.write_bytes(dummy_x64_pe())
            release = {
                'tag_name': 'v'+version,
                'body': '',
                'assets': [
                    {'name':asset, 'browser_download_url':'https://example.invalid/asset', 'digest':'sha256:'+digest},
                    {'name':f'npp.{version}.checksums.sha256', 'browser_download_url':'https://example.invalid/checksums'},
                ],
            }
            args = SimpleNamespace(version='', revision='b1r3', work=str(work),
                                   output=str(base/'dist'), launcher=str(launcher))
            with patch.object(npp, 'get_release', return_value=release), \
                 patch.object(npp, 'dereference_tag', return_value='a'*40), \
                 patch.object(npp, 'gh_request', return_value=checksums), \
                 patch.object(npp, 'copy_packaged_icons', side_effect=controlled_icons):
                first = npp.build(args)
                pkg = Path(first['stage_dir'])
                self.assertEqual((pkg/'App'/'Notepad++'/'doLocalConf.xml').read_bytes(), b'')
                self.assertEqual((pkg/'Other'/'Source'/'upstream-doLocalConf.xml.original').read_bytes(), payload)
                self.assertTrue((pkg/'Other'/'Source'/'PROVENANCE.json').is_file())
                self.assertEqual(json.loads((pkg/'Other'/'Source'/'PROVENANCE.json').read_text())['builder_revision'], 'b1r3')
                with zipfile.ZipFile(first['zip_path']) as z:
                    self.assertIn(f'{npp.ROOT}/App/Notepad++/plugins/config/empty/', z.namelist())
                    self.assertIsNone(z.testzip())
                # Identical inputs produce identical ZIP bytes even on a clean rebuild.
                second = npp.build(args)
                self.assertEqual(first['zip_sha256'], second['zip_sha256'])

    def test_zip_path_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'bad.zip'
            with zipfile.ZipFile(source,'w') as z: z.writestr('../host-file','BAD')
            with zipfile.ZipFile(source) as z:
                with self.assertRaises(ValueError): npp.secure_extract(z,Path(tmp)/'out')
            self.assertFalse((Path(tmp)/'host-file').exists())
    def test_zip_empty_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/npp.ROOT
            (root/'Data'/'Settings'/'empty').mkdir(parents=True)
            (root/'App').mkdir()
            archive=Path(tmp)/'test.zip'
            npp.create_zip(root,archive)
            with zipfile.ZipFile(archive) as z:
                self.assertIn(npp.ROOT+'/Data/Settings/empty/',z.namelist())
                self.assertIsNone(z.testzip())
            digest1=hashlib.sha256(archive.read_bytes()).hexdigest()
            time.sleep(0.01)
            npp.create_zip(root,archive)
            self.assertEqual(digest1,hashlib.sha256(archive.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
