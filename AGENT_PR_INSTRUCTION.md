# Pull Request Creation Workflow

This document outlines the steps I will take to create a Pull Request, emphasizing clarity and adherence to user instructions regarding branching. I will derive all the information I need by analyzing the code changes and using git commands without needing to ask the user other than to confirm my proposal.

## Tools available to me through shell command

* git
* gh

## Workflow for Creating a Pull Request

To ensure a smooth and correct Pull Request creation process, I will follow these steps, beginning with a clear directive to you:

1.  **Perform Git Status and Diff**:
    *   I will get the current status of your Git repository and the differences in your staged changes using:
        ```bash
        git status
        git diff
        ```
    *   Also check new files from git status since it might now show in git diff.

2.  **Summarize Changes with Conventional Commits**:
    *   I will summarize the changes based on the Conventional Commits specification, preparing the commit message.

3.  **Execute Branch Creation**:
    *   I will confirm my proposed branch name and then execute:
        ```bash
        git checkout -b <proposed-branch-name> origin/main
        ```
    *   I will then confirm that I have successfully switched to the new branch.

4.  **Commit Changes on Feature Branch**:
    *   I will commit the summarized changes to your local repository on the **new feature branch**:
        ```bash
        git commit -m "<Conventional Commit Message>"
        ```

5.  **Push Changes to Remote Feature Branch**:
    *   I will push the committed changes to the **new feature branch** on the remote repository:
        ```bash
        git push origin <proposed-feature-branch-name>
        ```

6.  **Create Pull Request**:
    *   Finally, I will attempt to create a Pull Request from my proposed new feature branch to the target branch (e.g., `main` or `master`). This step may involve further interaction if direct API access for PR creation is not available or if specific PR details are required.

This structured approach aims to prevent errors like committing to the wrong branch and ensures all necessary steps for a proper Pull Request are followed.
