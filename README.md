# Deep Researcher

## Overview

Deep Researcher is a Python-based research assistant that automates the process of in-depth research on a given topic. It leverages large language models (LLMs) through the OpenRouter API and search capabilities via the Perplexity API to break down complex research questions, execute dynamic searches, and generate comprehensive research reports.

## Features

*   **Research Direction Discussion:**  Initiates a conversation to refine the research topic and ensure it aligns with user needs.
*   **Task Analysis:** Decomposes a broad research topic into specific, actionable sub-questions and keywords for targeted searching.
*   **Dynamic Search:**  Performs iterative searches, analyzing results at each step to identify gaps and refine search queries for more complete coverage.
*   **Report Generation:**  Synthesizes findings from multiple search results into a well-structured research report with properly cited sources.

## Dependencies

*   Python 3.6+
*   `requests`
*   `collections`
*   `typing`
*   Perplexity API Key (set as environment variable `PERPLEXITY_API_KEY`)
*   OpenRouter API Key (set as environment variable `OPENROUTER_API_KEY`)

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/justinhuang0208/deep_research_with_sonar
    cd deep_researcher_with_sonar
    ```

2.  **Install dependencies (preferably in a virtual environment):**

3.  **Set environment variables:**

    You must set the `PERPLEXITY_API_KEY` and `OPENROUTER_API_KEY` environment variables with your respective API keys.  How you set these depends on your operating system:


## Usage

1.  **Run the `main.py` script:**

2.  **Follow the prompts:**  The script will ask you to enter the research topic.  It will then guide you through the research process, including discussions and refining the research direction (if needed).

3.  **Output:** The final research report will be saved as `research_report.md`. Intermediate search results and citation data are also stored in `search_results.md` and `citations.md` respectively. A file containing search results with global citations is saved as `search_results_with_global_citations.md`.

## Configuration

The following parameters can be adjusted within the `main.py` script to customize the research process:

*   `ANALYSIS_MODEL`:  Specifies the LLM model used for task analysis and planning (default: `"google/gemini-2.0-flash-001"`).  Experiment with different models available on OpenRouter.
*   `MAX_SEARCH_DEPTH`:  Controls the maximum number of iterative search refinements performed for each sub-question (default: `2`).  Increasing this value can lead to more comprehensive results but also increases processing time and API costs.
*   `MODEL_ENDPOINT`:  The OpenRouter API endpoint (default: `"https://api.openrouter.ai/v1/chat/completions"`).  Generally, you shouldn't need to change this.
*   `SEARCH_RESULTS_FILE`, `CITATIONS_FILE`, `SEARCH_RESULT_FILE_WITH_GLOBAL_CITATIONS`: Names of files for storing search results and citations.

## File Descriptions

* `main.py`: The main script that handles the research process, from taking user input to generatingthe final report.
* `search_results.md`: A file containing every search result, split into respective queries and citations.
* `search_results_with_global_citations.md`: A file containing all the search results including the global citation numbers.
* `research_report.md`: A file containing the final research report which is genereated integrating search query results with global citations.