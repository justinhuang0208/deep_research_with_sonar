import os
import json
import re
import logging
import requests
from openai import OpenAI
from collections import deque
from typing import List, Dict

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
SEARCH_RESULTS_FILE = "search_results.md"
SEARCH_RESULT_FILE_WITH_GLOBAL_CITATIONS = "search_results_with_global_citations.md"
DEFAULT_MODEL = "google/gemini-2.0-flash-001"
ANALYSIS_MODEL = "google/gemini-2.0-flash-001"
WRITING_MODEL = "google/gemini-2.0-flash-001"
MAX_SEARCH_DEPTH = 2
MODEL_ENDPOINT = "https://openrouter.ai/api/v1"

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def call_openrouter(prompt: str, history: List[Dict], model: str = DEFAULT_MODEL) -> Dict:
    """OpenRouter api call"""
    try:
        history.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=model,
            messages=history + [{"role": "user", "content": prompt}],
            temperature=1,
        )
        history.append({"role": "assistant", "content": response.choices[0].message.content})
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenRouter call failed: {str(e)}")
        return {"error": str(e)}

def call_perplexity(query: str, model: str = "sonar") -> Dict:
    """Call Perplexity API for search."""
    try:
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        content = """You are a world class research assistant; your sole job is to use the search tool to provide accurate search results based on the query with citations in the following format:
                - \"Ice is less dense than water[1][2].\" or \"Paris is the capital of France[1][4][5].\"
                - NO SPACE between the last word and the citation, and ALWAYS use brackets. Only use this format to cite search results. NEVER include a References section at the end of your answer.
                - If you don't know the answer or the premise is incorrect, explain why.
                If the search results are empty or unhelpful, answer the query as well as you can with existing knowledge.
                You MUST NEVER use moralization or hedging language. AVOID using the following phrases:
- "It is important to ..."
- "It is inappropriate ..."
- "It is subjective ..."
                You MUST ADHERE TO the following formatting instructions:
                - Use markdown to format paragraphs, lists, tables, and quotes whenever possible.
                - Avoid responding solely with lists; incorporate your answers into coherent paragraphs.
                - Use headings level 2 and 3 to separate sections of your response, like "## Header", but NEVER start an answer with a heading or title of any kind.
                - Use single new lines for lists and double new lines for paragraphs.
                - Use markdown to render images given in the search results.
                - NEVER write URLs or links"""
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": content},
                {"role": "user", "content": query}
            ],
            "temperature": 1
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload
        )
        result = response.json()
        return {
            "content": result['choices'][0]['message']['content'],
            "citations": result.get('citations', [])
        }
                
    except Exception as e:
        logger.error(f"Perplexity search failed: {str(e)}")
        return {"content": f"Search Error: {str(e)}", "citations": []}

def save_search_result(query: str, result: Dict):
    """Save search result to file."""
    with open(SEARCH_RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"# {query}\n")
        f.write("## content\n")
        f.write(result["content"] + "\n")
        f.write("## citations\n")
        if result["citations"]:
            for i, url in enumerate(result["citations"], 1):
                f.write(f"{i}. {url}\n")
        else:
            f.write("No citations available\n")
        f.write("***\n\n")

def process_citations():
    """Process global citation numbers and return replaced content."""
    # Read original file
    with open(SEARCH_RESULTS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by level 1 headers (paragraphs starting with "# ")
    sections = re.split(r'(?=^# .+$)', content, flags=re.MULTILINE)

    # Initialize global citation management
    global_citations = []
    current_global_id = 0

    # Process each section
    for i, section in enumerate(sections):
        if not section.strip():
            continue

        # Extract the citation part of the section
        citations_match = re.search(r'## citations\n([\s\S]+?)(?=\n##|\Z)', section)
        if not citations_match:
            continue

        # Extract the original citation list
        local_citations = re.findall(r'\d+\.\s+(https?://\S+)', citations_match.group(1))

        # Generate citation map: local ID -> global ID
        citation_map = {}
        for local_id, url in enumerate(local_citations, start=1):
            current_global_id += 1
            global_citations.append(f"{current_global_id}. {url}")
            citation_map[local_id] = current_global_id

        # Replace citation markers in the text
        def replace_citation(match):
            local_ids = [int(id) for id in re.findall(r'\d+', match.group(0))]
            global_ids = [str(citation_map[id]) for id in local_ids]
            return f"[{']['.join(global_ids)}]"

        updated_section = re.sub(r'\[\d+(?:][\d+]*)*\]', replace_citation, section)

        # Update the citation list of the section
        updated_section = re.sub(
            r'## citations\n[\s\S]+?(?=\n##|\Z)',
            f"## citations\n" + "\n".join(f"{citation_map[id]}. {url}" 
                                        for id, url in enumerate(local_citations, start=1)),
            updated_section,
            flags=re.DOTALL
        )

        sections[i] = updated_section

    # Merge the processed content
    processed_content = "\n".join(filter(None, sections))
    with open(SEARCH_RESULT_FILE_WITH_GLOBAL_CITATIONS, "w", encoding="utf-8") as f:
        f.write(processed_content)

    return processed_content

def analyze_task(query: str, history: List[Dict]) -> Dict:
    """Task analysis and planning"""
    
    prompt = """You need to break down the research topic into sub-questions and generate English search queries for each sub-question, describing the keywords in natural language, without using overly specific search terms.
    Keywords like "2024" or "launch date" should be avoided.
    For example sub-question: What are the differences in target markets and service offerings between Starlink and OneWeb in 2024?
    Can generate the following search questions:
    1. Starlink target market in 2024
    2. Starlink service offerings in 2024
    3. Oneweb target market in 2024
    4. Oneweb service offerings in 2024
    Response format example:
    {
        "sub_questions": [
            {
                "question": "Subproblem description",
                "keywords": ["Search term 1", "Search term 2"]
            }
        ]
    }"""
    
    response = call_openrouter(
        prompt=f"{prompt}\nResearch topic:{query}",
        history=history,
        model=ANALYSIS_MODEL
    )
    json_str = re.search(r'```json\n(.*?)\n```', response, re.DOTALL).group(1)
    return json.loads(json_str)

def execute_dynamic_search(sub_question: Dict, history: List[Dict]) -> Dict:
    """Execute dynamic search process (integrated result saving)"""

    search_queue = deque(sub_question["keywords"])
    processed = set()
    results = []

    for depth in range(MAX_SEARCH_DEPTH + 1):
        current_results = []

        while search_queue:
            query = search_queue.popleft()
            if query in processed:
                continue

            print(f"Searching [{sub_question['question']}] - {query}")
            result = call_perplexity(query)

            save_search_result(query, result)

            current_results.append(result["content"])
            processed.add(query)

        if depth < MAX_SEARCH_DEPTH and current_results:
            analysis_prompt = f"""Synthesize the following results:
            ## Sub Question:{sub_question['question']}
            ## Current Search Results:
            {current_results}
            please generate:
            1. Completeness score(0-100)
            2. Supplementary search directions needed (up to 3)
            3. New precise search terms (up to 3)
            Respond according to the following JSON format:
            ```json
            {{
                "score": Completeness score,
                "missing_info": ["Supplement Direction 1", "Supplement Direction 2"],
                "new_queries": ["New Search Term 1", "New Search Term 2"]
            }}
            ```"""
            analysis_response = call_openrouter(analysis_prompt, history, ANALYSIS_MODEL)
            json_match = re.search(r'```json\n(.*?)\n```', analysis_response, re.DOTALL)

            if json_match:
                json_string = json_match.group(1).strip()
                try:
                    analysis = json.loads(json_string)
                    if "new_queries" in analysis and analysis.get("score", 0) < 80:
                        print(f"Add supplementary search: {analysis['new_queries']}")
                        search_queue.extend(analysis["new_queries"])
                    else:
                        print("No supplementary search needed\n")
                except json.JSONDecodeError as e:
                    logger.error(f"JSONDecodeError: {e}")
                    logger.error(f"Problematic JSON string: {json_string}")
            else:
                logger.error("No JSON block found in analysis_response.")
                logger.error(f"Full analysis_response: {analysis_response}")

        results.extend(current_results)
        if not search_queue:
            break

def generate_research_report(history: List[Dict]) -> str:
    """Generate the final research report (integrated processed content)"""

    processed_content = process_citations()

    prompt = """Please merge the content from all search results, add appropriate text paragraphs, and expand it into an in-depth research report covering all search data. The report must mention all search results. Each important argument or data should be accompanied by the corresponding citation number, e.g.: [1][2]. Ensure the citation format is correct and accurate, while ordinary descriptions do not need to be cited; at the end of the report, list all the references you have used above in an ordered list. Please write in English."""
    return call_openrouter(
        prompt=prompt + "\n" + processed_content,
        history=history,
        model=WRITING_MODEL
    )

def main_flow():
    
    if not (PERPLEXITY_API_KEY or OPENROUTER_API_KEY):
        logger.error("Please set the environment variables PERPLEXITY_API_KEY and OPENROUTER_API_KEY.")
        return

    system_prompt = """You are a professional research assistant responsible for assisting users in conducting in-depth research.
                       You need to conduct research direction discussions, task analysis, dynamic search, and generate a final report based on the user's research topic.
                       1. Research direction discussion: Determine research goals, key aspects to explore and important themes, research depth, and research scope with the user.
                       2. Task analysis: Decompose the research direction discussed earlier into specific research tasks and generate specific research questions.
                       3. Analyze and comment on the current status of the research question to see if there is any content that needs to be supplemented.
                       4. Generate research report: Based on the previous research results and discussions, generate an in-depth research report that meets user expectations."""
    conversation_history = [{"role": "system", "content": system_prompt}]
    
    try:
        user_query = input("Please enter the research topic:")

        print("Performing initial search\n")
        init_search = call_perplexity(user_query, "sonar")['content']
        user_prompt = f"""Discuss the research direction with the user and correct.
                    This is the initial search result for this research topic, which gives you some preliminary understanding of the topic to propose the correct research direction: {init_search}
                    This is the research topic and content that the user wants: {user_query}"""
        print("\n" + call_openrouter(user_prompt, conversation_history))
        while True:
            comfirmation = input("Does the above research content meet your needs? (y/n)").lower()
            if comfirmation == "y":
                break
            else:
                user_query = input("Please re-enter the research topic:")
                print(call_openrouter(user_query, conversation_history))
        print("\n")
        
        # Task Analysis Stage
        print("Analyzing research tasks...")
        task_plan = analyze_task(user_query, conversation_history)
        
        # Dynamic Search Execution
        print("Starting to execute in-depth search...")
        for sub in task_plan["sub_questions"]:
            execute_dynamic_search(sub, conversation_history)
        
        # Generate Final Report
        print("Generating research report...")
        report = generate_research_report(conversation_history)
        
        # Save Results
        with open("research_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to: research_report.md")
        
    except Exception as e:
        logger.error(f"Process execution failed:{str(e)}")

if __name__ == "__main__":
    # Clear old files during initialization
    if os.path.exists(SEARCH_RESULTS_FILE):
        os.remove(SEARCH_RESULTS_FILE)
    
    main_flow()