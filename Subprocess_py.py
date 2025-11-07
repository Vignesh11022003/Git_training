import subprocess

import sys

import os

import shutil
cvbnm,.
def subprocess_run(command):

    try:

        output=subprocess.run(command,text=True,capture_output=True,shell=True)

        print(f"Running the command {command}")

        print(output.stdout)

        return output.stdout

    except Exception as E:

        print(f"Error Occurred While running the command {command}")

        print(f"Error Occurred {E} and exiting the process")

        sys.exit(1)
 
def convert_to_ssh_url(url):

    if url.startswith("https://"):

        url = url.replace("https://", "")

        parts = url.split('/')

        print ("URL contains https. Converting into git url")

        git_based_url = f"git@{parts[0]}:{'/'.join(parts[1:])}"

        print (git_based_url)

        return git_based_url

    else:

        print("Passed Url is SSH url no need for Parsing")

    return url 

def clone_repo(repoUrl):

    cloneCommand=f"git clone {repoUrl}"

    subprocess_run(cloneCommand)
 
def check_if_branch_exists(branch):

    checkBranchCommand="git branch -r"

    result = subprocess_run(checkBranchCommand)

    branches = []

    for line in result.splitlines():

        line = line.strip()

        if "->" in line:

            continue

        if line.startswith("origin/"):

            line = line.replace("origin/", "", 1)

        branches.append(line)

    branchExists=False

    for branchName in branches:

        if branch == branchName:

            branchExists=True

            break

        else:

            continue

    if branchExists:

        return True

    else:

        return False
 
def create_checkout_branch(checkoutBranch,externalBranch):

    subprocess_run(f"git checkout {checkoutBranch}")

    subprocess_run(f"git checkout -b {externalBranch}")

    subprocess_run("git branch")
 
def add_remote(remoteUrl):

    addRemoteUrl=f"git remote add Internal {remoteUrl}"

    subprocess_run(addRemoteUrl)

    fetchRemote="git fetch Internal"

    subprocess_run(fetchRemote)

def get_commit_list(previousReleasedTag,internalBranch):

    getCommitList=f"git rev-list --reverse --no-merges {previousReleasedTag}..Internal/{internalBranch}"

    commitList=subprocess_run(getCommitList)

    if not commitList.strip():

        print("No new commits found exiting the process")

        sys.exit(0)

    print("The received Commit Ids are :",commitList)

    return commitList

def handle_lfs(internalBranch):

    subprocess_run("git lfs install")

    subprocess_run("git lfs track")

    subprocess_run(f"git lfs fetch Internal {internalBranch}")

    subprocess_run(f"git lfs pull Internal {internalBranch}")

def cherry_pick_commit(commitId):

    cherryPickCommitCommand=f"git cherry-pick --strategy=recursive -X theirs {commitId} --no-edit"

    result=subprocess_run(cherryPickCommitCommand)

    if "error:" in result or "CONFLICT" in result:

        print(f"Conflict detected for {commitId}...keeping incoming changes.")

        subprocess_run("git checkout --theirs .")

        subprocess_run("git add .")

        subprocess_run("git cherry-pick --continue --no-edit")

def check_submodule_commit(commitId):

    output = subprocess_run(f"git diff-tree -r {commitId}")

    if "160000" in output:

        return 1

    else:

        return 0

def check_commit_path(commitList,tagName,externalBranch):

    try:

        for commitId in commitList.splitlines():

            checkpath= f"git show --pretty=format: --name-only {commitId}"

            path=subprocess_run(checkpath)

            if (".github/" in path.strip()):

                print(f"skipping commitId {commitId} as it has a change in .github folder.")

                continue

            elif(check_submodule_commit(commitId)):

                print(f"skipping commitId {commitId} as it belongs to Submodule Update.")

                continue

            else:

                cherry_pick_commit(commitId)

        push_commits(externalBranch)

        lastCommit=commitList.splitlines()[-1]

        create_tag_and_push(lastCommit,tagName)

    except Exception as E:

        print(f"Error Occurred : {E}")

        sys.exit(1)

def push_commits(branch):

    pushCommand=f"git push -u origin {branch}"

    subprocess_run(pushCommand)

def create_tag_and_push(lastCommit,tagName):

    createTag=f"git tag {tagName} {lastCommit}"

    subprocess_run(createTag)

    subprocess_run(f"git push Internal {tagName}")

if __name__ == "__main__":

    try:

        if len(sys.argv) < 7:

            print("Usage: python Incremental_Commit_Release.py <internalRepoUrl> <internalBranch> <previousReleasedTag> <externalRepoUrl> <externalBranch> <tagName> [<checkoutBranch>]")

        else:

            internalRepoUrl=sys.argv[1]

            internalBranch=sys.argv[2]

            previousReleasedTag=sys.argv[3]

            externalRepoUrl=sys.argv[4]

            externalBranch=sys.argv[5]

            tagName=sys.argv[6]

            sourceFolder=os.path.basename(externalRepoUrl)

            sourceFolder=sourceFolder.split('.')[0]
 
            internalRepoUrl=convert_to_ssh_url(internalRepoUrl)

            externalRepoUrl=convert_to_ssh_url(externalRepoUrl)

            if not os.path.exists(sourceFolder):

                clone_repo(externalRepoUrl)

                os.chdir(sourceFolder)

            else:

                print(f"External Repo {sourceFolder} exists...")

                try:

                    os.chdir(sourceFolder)

                except Exception as E:

                    print(f"Error Occurred While changing the dir {sourceFolder} ")

                    sys.exit(1)
 
            fetchRemoteCommand="git fetch origin"

            subprocess_run(fetchRemoteCommand)
 
            if check_if_branch_exists(externalBranch):

                print("Branch Already Exists")

            else:

                print(f"There is no such branch {externalBranch}")

                if len(sys.argv)==8:

                    if check_if_branch_exists(sys.argv[7]):

                        print(f"Source checkout branch {sys.argv[7]} ")

                        create_checkout_branch(sys.argv[7],externalBranch)

                    else:

                        print("No Such source branch to checkout,give valid branch to checkout")

                        sys.exit(1)

                else:

                    print("Pass the source branch from where target branch is needs to be created")

                    sys.exit(1)
 
            subprocess_run(f"git checkout {externalBranch}")

            add_remote(internalRepoUrl)

            handle_lfs(internalBranch)

            commitList=get_commit_list(previousReleasedTag,internalBranch)

            check_commit_path(commitList,tagName,externalBranch)

    except Exception as E:

        print(f"Error Occurred {E}")

        sys.exit(1)
 
