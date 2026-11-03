"""Keep the established data location, separate from installed application files."""
import os
from pathlib import Path

def data_dir():
    path = Path(os.environ.get('AINAK_DATA_DIR', str(Path.home()/'AinakMahal')))
    path.mkdir(parents=True, exist_ok=True)
    return path

class InstanceLock:
    """OS-owned lock prevents restore or a second UI while a database is open."""
    def __init__(self, directory):
        self.file = open(Path(directory)/'application.lock','a+b')
        self.file.seek(0); self.file.write(b'0'); self.file.flush(); self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('Ainak Mahal is already open. Close it before opening or restoring data.') from None
    def close(self):
        self.file.close()
