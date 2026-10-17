import unittest
import subprocess,sys
from pathlib import Path

class Phase8Tests(unittest.TestCase):
    def test_app_cannot_be_started_directly(self):
        p=subprocess.run([sys.executable,str(Path(__file__).with_name('app.py'))],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('Start Ainak Mahal using launcher.py',p.stderr)
    def test_session_is_not_cli_controlled(self):
        p=subprocess.run([sys.executable,str(Path(__file__).with_name('app.py')),'--role','admin','--user','any'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
    def test_session_lifecycle(self):
        import auth_session
        self.assertIsNone(auth_session.current_session())
        auth_session.start_session('test','cashier')
        self.assertEqual(auth_session.current_session()['role'],'cashier')
        with self.assertRaises(RuntimeError):auth_session.start_session('other','admin')

if __name__=='__main__':unittest.main()
