# GitHub Actions Workflows

This directory contains the GitHub Actions workflows for this repository. The following diagram illustrates the triggers, jobs, and dependencies of these workflows.

```mermaid
graph TD
    %% Workflow Triggers
    subgraph Triggers
        PR_Created[Pull Request Created (to main)] --> PR_Workflow(pr-workflow.yml)
        PR_Comment[Issue Comment @gemini-cli /review] --> Gemini_PR_Review(gemini-pr-review.yml)
        Push_Main[Push to main branch] --> Test_Coverage(test-coverage.yml)
        Push_Main --> E2E_Tests(test-e2e.yml)
        Push_Docs[Push to main (docs/**)] --> GH_Pages(gh-pages.yml)
        Push_Tag[Push to Tag (v*)] --> Publish(publish.yml)
        Nightly_Schedule[Nightly Schedule (0 0 * * *)] --> Nightly_Build(nightly.yml)
        Manual_Dispatch[Manual Trigger (workflow_dispatch)] --> PR_Workflow
        Manual_Dispatch --> Test_Coverage
        Manual_Dispatch --> E2E_Tests
        Manual_Dispatch --> Gemini_PR_Review
        Manual_Dispatch --> GH_Pages
        Manual_Dispatch --> Nightly_Build
    end

    %% Reusable Workflow
    subgraph Reusable Workflows
        Reusable_Python_Test[reusable-python-test-coverage.yml]
    end

    %% Main Workflows and their jobs
    subgraph Workflows
        PR_Workflow --> Lint(pr-workflow.yml: Lint Code)
        PR_Workflow --> Call_Test_Coverage_PR(pr-workflow.yml: Run Tests and Coverage)
        Lint --> PR_Comment_Notify(pr-workflow.yml: PR Comment and Notifications)
        Call_Test_Coverage_PR --> PR_Comment_Notify

        Test_Coverage --> Call_Test_Coverage_TC(test-coverage.yml: Run Tests and Coverage Analysis)
        Call_Test_Coverage_TC --> Sonar_Report(test-coverage.yml: Report SonarQube)

        E2E_Tests --> Run_E2E(test-e2e.yml: Run End-to-End Tests)

        Gemini_PR_Review --> Review_PR_Job(gemini-pr-review.yml: Review PR)

        GH_Pages --> Build_Jekyll(gh-pages.yml: Build Jekyll Site)
        Build_Jekyll --> Deploy_Pages(gh-pages.yml: Deploy to GitHub Pages)

        Publish --> Publish_PyPI(publish.yml: Publish to PyPI)

        Nightly_Build --> Test_Latest(nightly.yml: Test with Latest Dependencies)
    end

    %% Workflow Calls
    Call_Test_Coverage_PR -- calls --> Reusable_Python_Test
    Call_Test_Coverage_TC -- calls --> Reusable_Python_Test

    %% Dependencies (explicit needs)
    PR_Comment_Notify -- needs --> Lint
    PR_Comment_Notify -- needs --> Call_Test_Coverage_PR
    Sonar_Report -- needs --> Call_Test_Coverage_TC
    Deploy_Pages -- needs --> Build_Jekyll

    %% Implied Flow (within jobs if not explicit needs)
    GH_Pages_Build_Artifact[gh-pages.yml: Upload artifact] --> GH_Pages_Deploy_Download[gh-pages.yml: Deploy to GitHub Pages (downloads artifact)]
    Test_Coverage_Artifact[test-coverage.yml: Upload test-and-coverage-reports] --> Sonar_Report_Download[test-coverage.yml: Report SonarQube (downloads artifact)]
```