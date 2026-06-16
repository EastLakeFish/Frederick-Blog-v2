#! /bin/env python

"""
(c) eastlakefish.com
Deploy the website.
"""

import argparse
import subprocess


def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return f"[{command}]: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"(ERR)[{command}]\n{e.stderr.strip()}"
    

def git_commit(message):
    print("-------- GIT --------")
    for command in (
        ("git", "add", "."),
        ("git", "commit", "-m", message),
        ("git", "push"),
    ):
        print(run_command(command))
    print("-------- GIT --------")
        

def web_deploy():
    print("----- NPM DEPLOY ----")
    print(run_command(("sudo", "npm", "run", "deploy")))
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
    