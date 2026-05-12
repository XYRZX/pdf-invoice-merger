import os

application_path = defines.get("app", os.path.join("dist", "InvoiceMerge.app"))
appname = defines.get("appname", "InvoiceMerge")
application = os.path.basename(application_path)

files = [(application_path, application)]
symlinks = {"Applications": "/Applications"}

icon_locations = {
    application: (140, 120),
    "Applications": (420, 120),
}

window_rect = ((200, 200), (580, 320))
background = None
