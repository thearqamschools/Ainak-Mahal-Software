"""Generate a fresh build ID and matching EXE/installer resource metadata."""
import json,os,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from app_info import VERSION,DEVELOPER,PRODUCT_NAME

def generate():
    stamp=datetime.now(timezone.utc)
    try:
        sha=subprocess.check_output(['git','-c','safe.directory='+str(root),'rev-parse','--short=8','HEAD'],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):sha='source'
    try:
        dirty=bool(subprocess.check_output(['git','-c','safe.directory='+str(root),'status','--porcelain'],cwd=root,text=True,stderr=subprocess.DEVNULL).strip())
    except (OSError,subprocess.CalledProcessError):dirty=False
    run=os.environ.get('GITHUB_RUN_NUMBER')
    build_id=stamp.strftime('%Y%m%dT%H%M%SZ')+'-'+('ci'+run+'.'+os.environ.get('GITHUB_RUN_ATTEMPT','1') if run else 'local')+'-'+sha
    if dirty:build_id+='-dirty'
    revision=int(run) if run else (stamp.hour*3600+stamp.minute*60+stamp.second)%65536
    if not 0<=revision<=65535:raise ValueError('Build revision exceeds Windows resource limits; increment the release version and reset the CI build series')
    version=tuple(int(p) for p in VERSION.split('.'))+(revision,)
    if len(version)!=4 or any(not 0<=p<=65535 for p in version):raise ValueError('Release version must have three numeric components, each within Windows limits')
    file_version='.'.join(map(str,version))
    generated=root/'build';generated.mkdir(exist_ok=True)
    (root/'_build_info.py').write_text(f'BUILD_ID = {build_id!r}\nFILE_VERSION = {version!r}\n',encoding='utf-8')
    strings={'CompanyName':DEVELOPER,'FileDescription':'Ainak Mahal Offline Optical Store ERP',
             'FileVersion':file_version,'InternalName':'AinakMahal','OriginalFilename':'AinakMahal.exe',
             'ProductName':PRODUCT_NAME,'ProductVersion':VERSION+' (build '+build_id+')',
             'Comments':'Developed by '+DEVELOPER}
    entries=',\n'.join(f'StringStruct({key!r}, {val!r})' for key,val in strings.items())
    resource=f'''VSVersionInfo(ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [{entries}])]), VarFileInfo([VarStruct('Translation', [1033,1200])])])'''
    (generated/'windows-version.txt').write_text(resource,encoding='utf-8')
    metadata={'version':VERSION,'file_version':file_version,'build_id':build_id,'developer':DEVELOPER,'source_commit':sha,'source_dirty':dirty,'built_utc':stamp.isoformat()}
    (generated/'release-metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata))

if __name__=='__main__':generate()
