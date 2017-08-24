import sys
from cx_Freeze import setup, Executable

base = None
include_files = ["./static", "./templates", "./db"]

if sys.platform == "win32":
    base = "Console"

setup(name = "Institution_Name",
    version = "0.1.0",
    description = "Student_Record_System",
    options = {
        "build_exe" : {
            'packages': ['encodings', 'asyncio', 'flask', 'cs50', 'sqlalchemy', 'jinja2', 'flask_compress', 'passlib', 'werkzeug', 'uuid', 'os', 'operator'],
            "include_files" : include_files
            }
    },
    executables = [Executable("app.py", base=base, targetName="Institution_Name.exe", icon="static/img/system/logo.ico")]
)
