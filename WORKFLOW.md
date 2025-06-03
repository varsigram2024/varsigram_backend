# **Git Workflow Guide for Our Django Project**

Welcome to the Git Workflow Guide for our Django project! This document outlines the branching strategy and workflow we use to collaborate effectively. Follow these steps to ensure smooth development and deployment.

---

## **Branches Overview**

We use a structured branching workflow based on Gitflow. Below are the branches and their purposes:

| Branch        | Purpose                                                |
|---------------|--------------------------------------------------------|
| `main`        | Contains production-ready code.                        |
| `develop`     | Contains the latest integrated development code.       |
| `feature`     | Used for developing new features.                      |
| `bugfix`      | Used to fix bugs in the `develop` branch.              |
| `release`     | Used to prepare the code for a production release.     |
| `hotfix`      | Used for urgent fixes on the `main` branch.            |

---

## **General Workflow**

1. **Clone the Repository**  
   Clone the repository to your local machine if you haven’t already:  
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Set Up the Repository**  
   Ensure you have the latest code from the `main` and `develop` branches:  
   ```bash
   git checkout main
   git pull origin main

   git checkout develop
   git pull origin develop
   ```

---

## **Working on a Feature**

When adding a new feature:

1. **Create a New Feature Branch**  
   Always create a branch off of `develop`:  
   ```bash
   git checkout develop
   git checkout -b feature/<feature-name>
   ```

2. **Develop and Commit Changes**  
   Regularly commit your changes with clear messages:  
   ```bash
   git add .
   git commit -m "Add feature: <brief description>"
   ```

3. **Merge Feature into Develop**  
   Once your feature is complete:  
   ```bash
   git checkout develop
   git merge feature/<feature-name>
   git branch -d feature/<feature-name>
   git push origin develop
   ```

---

## **Fixing a Bug**

When fixing bugs during development:

1. **Create a Bugfix Branch**  
   Create the branch from `develop`:  
   ```bash
   git checkout develop
   git checkout -b bugfix/<bug-name>
   ```

2. **Fix the Bug and Commit Changes**  
   Commit your fixes:  
   ```bash
   git add .
   git commit -m "Fix bug: <brief description>"
   ```

3. **Merge Bugfix into Develop**  
   Once the fix is complete:  
   ```bash
   git checkout develop
   git merge bugfix/<bug-name>
   git branch -d bugfix/<bug-name>
   git push origin develop
   ```

---

## **Preparing for a Release**

When preparing a release:

1. **Create a Release Branch**  
   Branch off `develop`:  
   ```bash
   git checkout develop
   git checkout -b release/<version>
   ```

2. **Test and Fix Minor Issues**  
   Make necessary adjustments during testing.

3. **Merge Release into Main and Develop**  
   Once ready, merge the release branch:  
   ```bash
   git checkout main
   git merge release/<version>
   git push origin main

   git checkout develop
   git merge release/<version>
   git push origin develop
   ```

4. **Delete the Release Branch**  
   ```bash
   git branch -d release/<version>
   ```

---

## **Urgent Hotfixes**

For critical production issues:

1. **Create a Hotfix Branch**  
   Branch off `main`:  
   ```bash
   git checkout main
   git checkout -b hotfix/<fix-name>
   ```

2. **Fix the Issue and Commit Changes**  
   Commit the fix:  
   ```bash
   git add .
   git commit -m "Hotfix: <brief description>"
   ```

3. **Merge Hotfix into Main and Develop**  
   ```bash
   git checkout main
   git merge hotfix/<fix-name>
   git push origin main

   git checkout develop
   git merge hotfix/<fix-name>
   git push origin develop
   ```

4. **Delete the Hotfix Branch**  
   ```bash
   git branch -d hotfix/<fix-name>
   ```

---

## **Branch Naming Conventions**

Follow these naming conventions for consistency:

| Branch Type | Naming Format                | Example                 |
|-------------|------------------------------|-------------------------|
| Feature     | `feature/<feature-name>`     | `feature/user-login`    |
| Bugfix      | `bugfix/<bug-name>`          | `bugfix/fix-login-error`|
| Release     | `release/<version>`          | `release/1.0.0`         |
| Hotfix      | `hotfix/<fix-name>`          | `hotfix/urgent-404-fix` |

---

## **Tips for Collaboration**

1. **Pull Often:** Always pull the latest changes from `develop` or `main` before starting work:  
   ```bash
   git pull origin develop
   ```

2. **Write Clear Commit Messages:** Use descriptive messages to make commits meaningful.

3. **Avoid Committing Secrets:** Never commit sensitive information like passwords or API keys.

4. **Review Before Merging:** Always test your code before merging into `develop` or `main`.

---

This workflow ensures we maintain a clean, organized repository and work collaboratively without conflicts. If you have any questions, feel free to ask!  

Happy coding! 🚀
```