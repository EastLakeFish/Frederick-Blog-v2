#! /bin/env python

"""
(c) eastlakefish.com
Deploy the website.
"""

import argparse
import itertools
import subprocess
import sys
import threading
import time


def overwrite(msg, newline=False):
    sys.stdout.write('\r' + msg)
    if newline:
        sys.stdout.write('\n')
    sys.stdout.flush()


def spinner(stop_loading, command_str):
    spinner = itertools.cycle([
        "⠋",
        "⠙",
        "⠹",
        "⠸",
        "⠼",
        "⠴",
        "⠦",
        "⠧",
        "⠇",
        "⠏",
    ])
    while not stop_loading.is_set():
        overwrite("  ".join((next(spinner), command_str)))
        time.sleep(0.12)


def run_command(command):
    stop_loading = threading.Event()
    command_str = " ".join(command)
    msg = f"[{command_str}]"
    spinner_thread = threading.Thread(
        target=spinner,
        args=(stop_loading, command_str)
    )
    spinner_thread.start()
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        msg = f"{msg}\n{result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        msg = f"(ERR){msg}\n{e.stderr.strip()}"
    finally:
        stop_loading.set()
        spinner_thread.join()
        overwrite(msg, newline=True)
        

def git_commit(message):
    print("-------- GIT --------")
    for command in (
        ("git", "add", "."),
        ("git", "commit", "-m", message),
        ("git", "push"),
    ):
        run_command(command)
    print("-------- GIT --------")
        

def web_deploy():
    print("----- NPM DEPLOY ----")
    run_command(("sudo", "npm", "run", "deploy"))
    print("----- NPM DEPLOY ----")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-git", action="store_true")
    parser.add_argument("-m", "--message", type=str, default=None)
    args = parser.parse_args()
    
    if not args.skip_git:
        if args.message is None:
            msg = "auto-commit"
        else:
            msg = args.message
        git_commit(msg)
    
    web_deploy()
    