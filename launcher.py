"""Default Ainak Mahal desktop entry point. Legacy UI is retained explicitly."""
import sys

def main():
    if '--legacy' in sys.argv:
        from tk_launcher import main as legacy
        return legacy()
    from qt_launcher import main as desktop
    return desktop()

if __name__=='__main__':sys.exit(main())
