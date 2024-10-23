code = """
from ctypes import cast, POINTER
import pycaw.pycaw as pycaw
import pythoncom

def set_volume(volume):
    devices = pycaw.AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        pycaw.IAudioEndpointVolume._iid_, pythoncom.CLSCTX_ALL, None)
    volume_interface = cast(interface, POINTER(pycaw.IAudioEndpointVolume))
    volume_interface.SetMasterVolumeLevelScalar(volume, None)

# Ajuste este valor entre 0.0 e 1.0 para definir o volume desejado
volume_level = 0.75
set_volume(volume_level)
"""

exec(code)