import os
import shutil
import subprocess
import sys


here = os.path.dirname(__file__)
venv = os.path.join(here, "venv")

# Create a virtualenv if it doesn’t exist
if not os.path.isdir(venv):
    exit_code = subprocess.call(["virtualenv", "-p", sys.executable, venv])
    if exit_code:
        sys.exit(exit_code)

# Install requirements with pip, unless we already have
requirements_file = os.path.join(here, "requirements.txt")
requirements = open(requirements_file).read()

installed_file = os.path.join(venv, "installed-requirements")
try:
    installed = open(installed_file).read()
except OSError:
    installed = ""

if installed != requirements:
    pip = os.path.join(venv, "bin", "pip")
    exit_code = subprocess.call([pip, "install", "-r", requirements_file])
    if exit_code:
        sys.exit(exit_code)
    shutil.copyfile(requirements_file, installed_file)

# Execute the tc-admin app in this directory
tc_admin = os.path.join(venv, "bin", "tc-admin")
sys.exit(subprocess.call([tc_admin] + sys.argv[1:], cwd=here))
