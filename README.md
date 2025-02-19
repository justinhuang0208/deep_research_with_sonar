# Deep Research with Sonar

## Overview

Deep Research with Sonar is a Python-based research assistant that automates the process of in-depth research on a given topic. It leverages large language models (LLMs) through the OpenRouter API and search capabilities via the Perplexity API to break down complex research questions, execute dynamic searches, and generate comprehensive research reports.  The system saves intermediate search results and citations, enabling traceable and reproducible research.

## Features

*   **Research Direction Discussion:**  Initiates a conversation to refine the research topic and ensure it aligns with user needs.  This interactive process helps to define the scope, goals, and key aspects of the research.
*   **Task Analysis:** Decomposes a broad research topic into specific, actionable sub-questions and associated search queries for targeted searching.
*   **Dynamic Search:**  Performs iterative searches, analyzing results at each step to identify gaps and refine search queries for more complete coverage. The search depth is configurable.
*   **Report Generation:**  Synthesizes findings from multiple search results into a well-structured research report with properly cited sources using global citation numbering. The report includes all search results while citing specific claims and data.
*   **Automatic Citation:**  Automatically extracts and manages citations from search results, assigning global IDs for consistent referencing within the report.
*   **Persistent Storage:** Saves search results, citation data, and the final research report to files for later review and analysis.

## Dependencies

*   Python 3.6+
*   `requests`
*   `aiohttp`
*   `collections`
*   `typing`
*   `re`
*   `json`
*   `asyncio`
*   Perplexity API Key (set as environment variable `PERPLEXITY_API_KEY`)
*   OpenRouter API Key (set as environment variable `OPENROUTER_API_KEY`)

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/justinhuang0208/deep_research_with_sonar.git
    cd deep_research_with_sonar
    ```

2.  **Set environment variables:**

    You must set the `PERPLEXITY_API_KEY` and `OPENROUTER_API_KEY` environment variables with your respective API keys.  How you set these depends on your operating system:

    *   **Linux/macOS:**
        ```bash
        export PERPLEXITY_API_KEY="YOUR_PERPLEXITY_API_KEY"
        export OPENROUTER_API_KEY="YOUR_OPENROUTER_API_KEY"
        ```
        Add these lines to your `.bashrc` or `.zshrc` file for persistence.

    *   **Windows:**

        Use the `setx` command:

        ```powershell
        setx PERPLEXITY_API_KEY "YOUR_PERPLEXITY_API_KEY"
        setx OPENROUTER_API_KEY "YOUR_OPENROUTER_API_KEY"
        ```
        Note: Changes made with `setx` require a restart of the command prompt or PowerShell session to take effect. Alternatively, set the env vars via the 'Environment Variables' UI

## Usage

1.  **Run the `main.py` script:**

    ```bash
    python main.py
    ```

2.  **Follow the prompts:**  The script will ask you to enter the research topic and the maximum search depth. It will then guide you through the research process, including discussions to refine the research direction.  You'll be prompted regarding the necessity of an initial search using Perplexity.

3.  **Output:** The final research report will be saved as `research_report.md`. Intermediate files are also created:

    *   `search_results.md`: Contains raw search results, including content and citations, for each query.
    *   `search_results_with_global_citations.md`:  Contains the same search results, but with in-text citation markers replaced by global citation IDs.
    *   `research_report.md`: The completed research report, incorporating findings from the searches and using global citation IDs.

## Configuration

The following parameters can be adjusted within the `main.py` script to customize the research process:

*   `ANALYSIS_MODEL`:  Specifies the LLM model used for task analysis and planning (default: `"google/gemini-2.0-flash-001"`).  Experiment with different models available on OpenRouter.
*   `WRITING_MODEL`: Specifies the LLM model used for report generation (default: `"google/gemini-2.0-flash-001"`). 
*   `MAX_SEARCH_DEPTH`:  Controls the maximum number of iterative search refinements performed for each sub-question.  Increasing this value can lead to more comprehensive results but also increases processing time and API costs.
*   `MODEL_ENDPOINT`:  The OpenRouter API endpoint (default: `"https://api.openrouter.ai/v1/chat/completions"`).
*   `SEARCH_RESULTS_FILE`: Name of the file where raw search results and citations are stored (default: `"search_results.md"`).
*   `SEARCH_RESULT_FILE_WITH_GLOBAL_CITATIONS`: Name of the file where search results with global citation markers are stored (default: `"search_results_with_global_citations.md"`).
*   `RESEARCH_REPORT_FILE`: Name of the final research report file (default: `"research_report.md"`).

## File Descriptions

* `main.py`: The main script that handles the research process, from taking user input to generating the final report.
* `search_results.md`: A file containing every raw search result, split into respective queries and citations.
* `search_results_with_global_citations.md`: A file containing all the search results including the global citation numbers, replacing the local citations.
* `research_report.md`: A file containing the final research report which is generated by integrating search query results with global citations.

## Error Handling

The script includes basic error handling and logging.  Check the console output for any error messages. The logging is printed to the console and can be configured using the `logger` object in `main.py`.
