from invoke import task
import os
import shutil
import errno
import glob
import time
import subprocess
import pdb


# ---------------------------------------GLOBAL VARIABLES------------------------------------------#
# Path to user plugins/tools
alteryx_engine = f"C:\\Program Files\\Alteryx\\bin\\AlteryxEngineCmd.exe"
alteryx_miniconda = f"C:\\Program Files\\Alteryx\\bin\\Miniconda3\\python.exe"
try:
    user_tools_path = os.path.join(f"{os.environ['APPDATA']}", "Alteryx", "Tools")
except KeyError:
    print(
        "Not able to find APPDATA environment variable. This is expected on Linux/Gitlab CI"
    )
snakeplane_path = os.path.join("..", "snakeplane")
extras = []


# -------------------------------------------------------------------------------------------------#

# ---------------------------------------HELPER FUNCTIONS------------------------------------------#
def copy_files(src: str, dest: str, files_list: list):
    """Copies files from a source directory to a destination directory.

    Parameters
    ----------
    src : str
        The source directory
    dest : str
        The destination directory
    files_list : list
        The list of file names to be copied

    """
    for file_name in files_list:
        source = f"{src}/{file_name}"
        target = f"{dest}/{file_name}"
        print(source, target)
        copy_and_create_dir(source, target)
        print(f"Copied {file_name} from {src} to {dest}")


def copy_and_create_dir(src: str, dest: str):
    """Copies a file to a destination. Creates the directory if it doesn't exist.

    Parameters
    ----------
    src : str
        The source file
    dest : str
        The destination file

    """
    try:
        shutil.copyfile(src, dest)
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)


def del_directory(path: str):
    """Deletes a directory

    Parameters
    ----------
    path : str
        The path to the directory

    """
    if os.path.exists(path):
        print(f"Deleting {path} directory and contents")
        shutil.rmtree(path)


def delete_and_copy_to_dest_dir(src: str, dest: str):
    """Copies a source directory and overwrites the destination directory

    Parameters
    ----------
    src : str
        Path to the source directory
    dest : str
        Path to the destination directory

    """
    del_directory(dest)
    time.sleep(0.5)
    print(f"Copying {src} dir and contents to {dest}")
    shutil.copytree(src, dest)


# -------------------------------------------------------------------------------------------------#


def copy_src_engine_code(tool_name: str, tools_src_dir: str, package_dir: str):
    copy_and_create_dir(
        f"{tools_src_dir}/{tool_name}/engine/src/main.py",
        f"{package_dir}/{tool_name}/main.py",
    )
    copy_and_create_dir(
        f"env/requirements.txt", f"{package_dir}/{tool_name}/requirements.txt"
    )


def copy_bat_scripts(tool_name: str, tools_src_dir: str, package_dir: str):
    copy_and_create_dir(
        f"installer/installer.bat", f"{package_dir}/{tool_name}/installer.bat"
    )


def copy_gui_code(tool_name: str, tools_src_dir: str, package_dir: str):
    copy_files(
        f"{tools_src_dir}/{tool_name}/gui",
        f"{package_dir}/{tool_name}/gui",
        [f"{tool_name}Gui.html"],
    )


def copy_snakeplane(tool_name: str, tools_src_dir: str, package_dir: str):
    delete_and_copy_to_dest_dir(
        snakeplane_path, f"{package_dir}/{tool_name}/snakeplane"
    )


def copy_config_files(tool_name: str, tools_src_dir: str, package_dir: str):
    copy_files(
        f"{tools_src_dir}/{tool_name}/config",
        f"{package_dir}/{tool_name}",
        [f"{tool_name}Config.xml", f"{tool_name}Icon.png"],
    )


def copy_extras(tool_name: str, tools_src_dir: str, package_dir: str):
    for dir in extras:
        delete_and_copy_to_dest_dir(
            f"{tools_src_dir}/{tool_name}/{dir}", f"{package_dir}/{tool_name}/{dir}"
        )


def build_tool_target_dir(tool_name: str, tools_src_dir: str, package_dir: str):
    del_directory(f"{package_dir}/{tool_name}/")
    copy_src_engine_code(tool_name, tools_src_dir, package_dir)
    copy_gui_code(tool_name, tools_src_dir, package_dir)
    copy_snakeplane(tool_name, tools_src_dir, package_dir)
    copy_extras(tool_name, tools_src_dir, package_dir)
    copy_config_files(tool_name, tools_src_dir, package_dir)
    # copy_bat_scripts(tool_name, tools_src_dir, package_dir)


def move_to_tools_folder(tool_name: str, package_dir: str):
    dirs_list = ["gui", "snakeplane"] + extras
    files_list = [
        "main.py",
        f"{tool_name}Config.xml",
        f"{tool_name}Icon.png",
        "requirements.txt",
    ]

    try:
        tool_develop_mode_path = os.path.join(user_tools_path, tool_name)
    except NameError:
        # If the user_tools_path variable doesn't exist, then we're running in Linux/Gitlab CI
        # and should not try to finish this function
        return

    for dir in dirs_list:
        delete_and_copy_to_dest_dir(
            f"{package_dir}/{tool_name}/{dir}", f"{tool_develop_mode_path}/{dir}"
        )

    copy_files(f"{package_dir}/{tool_name}", f"{tool_develop_mode_path}", files_list)


# -------------------------------------------------------------------------------------------------#


@task(
    help={
        "name": "Name of the tool to be built",
        "src": "The source folder",
        "package": "The package folder",
        "update-requirements": "Installs new pip requirements from requirements.txt",
    }
)
def build(c, name, src="src", package="package", update_requirements=False):
    """
    Builds the tool and deploys it into Alteryx as well as into a folder for packaging.
    """
    if (
        os.path.exists(f"{src}/{name}")
        and os.path.exists(f"{src}")
        and os.path.exists(f"{package}")
    ):
        build_tool_target_dir(name, src, package)
        move_to_tools_folder(name, package)

        if update_requirements:
            venv(c, name)

    else:
        raise ValueError(f"The specified tool ({name}) cannot be found.")


@task(
    help={
        "name": "Specified name for the yxi",
        "package": "The folder you want to bundle. Default is package",
    }
)
def package(c, name, package="package"):
    """
    Bundles a folder into a yxi
    """
    shutil.make_archive(f"target_yxis/{name}", "zip", f"{package}")
    if os.path.exists(f"target_yxis/{name}.yxi"):
        os.remove(f"target_yxis/{name}.yxi")
    os.rename(f"target_yxis/{name}.zip", f"target_yxis/{name}.yxi")


@task
def venv(c, tool_name):
    """
    Creates and updates the venv inside of a tools folder
    """
    try:
        tool_path = os.path.join(user_tools_path, tool_name)
    except NameError:
        # If the user_tools_path variable doesn't exist, then we're running in Linux/Gitlab CI
        # and should not try to finish this function
        return

    if not os.path.exists(tool_path):
        raise ValueError(f"{tool_name} doesn't exist.")

    print("Checking Venv")
    subprocess.call(
        [
            "C:\\WINDOWS\\system32\\WindowsPowerShell\\v1.0\\powershell.exe",
            f"& '{alteryx_miniconda}' -m venv '{tool_path}'",
        ]
    )
    print("Installing new requirements")
    subprocess.call(
        [
            "C:\\WINDOWS\\system32\\WindowsPowerShell\\v1.0\\powershell.exe",
            f"& '{tool_path}/Scripts/pip.exe' install -r '{tool_path}/requirements.txt'",
        ]
    )


@task
def debug(c, name):
    """
    Run's the tool's debug workflow in the console
    """
    workflow = f"./debug_workflows/{name}.yxmd"

    if not os.path.exists(workflow):
        print(f"{name}.yxmd does not exist.\nYou need to setup a debug workflow")
        return
    subprocess.call(
        [
            "C:\\WINDOWS\\system32\\WindowsPowerShell\\v1.0\\powershell.exe",
            f"& '{alteryx_engine}' {workflow}",
        ]
    )


@task
def freeze(c):
    """
    Saves the workspaces current dependencies
    """
    subprocess.call(
        [
            "C:\\WINDOWS\\system32\\WindowsPowerShell\\v1.0\\powershell.exe",
            f"./env/Scripts/pip.exe freeze > ./env/requirements.txt",
        ]
    )

