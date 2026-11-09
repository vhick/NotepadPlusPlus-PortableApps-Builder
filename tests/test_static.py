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
