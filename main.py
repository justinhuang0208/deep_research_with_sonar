import asyncio
import aiohttp
import os
import json
import re
import logging
from openai import OpenAI
from collections import deque
from typing import List, Dict
from datetime import date

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
RESEARCH_REPORT_FILE = "research_report.md"
SEARCH_RESULTS_FILE = "search_results.md"
SEARCH_RESULT_FILE_WITH_GLOBAL_CITATIONS = "search_results_with_global_citations.md"
DEFAULT_MODEL = "google/gemini-2.0-flash-001"
ANALYSIS_MODEL = "deepseek/deepseek-r1"
WRITING_MODEL = "google/gemini-2.0-flash-001"
MAX_SEARCH_DEPTH = 2
MODEL_ENDPOINT = "https://openrouter.ai/api/v1"

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def call_openrouter(prompt: str, history: List[Dict], model: str = DEFAULT_MODEL) -> str:
    """Call OpenRouter API for chat completion."""
    try:
        history.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=model,
            messages=history + [{"role": "user", "content": prompt}],
            temperature=1
        )
        history.append({"role": "assistant", "content": response.choices[0].message.content})
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenRouter call failed: {str(e)}")
        return {"error": str(e)}

async def call_perplexity_async(session: aiohttp.ClientSession, query: str, model: str = "sonar") -> Dict:
    """Asyncornously call Perplexity API."""
    try:
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }

        content = """Your job is to use the search tool to provide accurate search results.
                The citation format is [number] and should be used to reference the search results in the final answer, especially the statment of numbers.
                - NO SPACE between the last word and the citation, and ALWAYS use brackets. Only use this format to cite search results. NEVER include a References section at the end of your answer.
                - If you don't know the answer or the premise is incorrect, explain why.
                If the search results are empty or unhelpful, answer the query as well as you can with existing knowledge.
                Make users can understand your arguments clearly without having to click on citations.
                You MUST ADHERE TO the following formatting instructions:
                - Use markdown to format paragraphs, lists, tables, and quotes whenever possible.
                - Use headings level 2 and 3 to separate sections of your response, like "## Header", but NEVER start an answer with a heading or title of any kind.
                - NEVER write URLs or links"""

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": content},
                {"role": "user", "content": query}
            ],
            "temperature": 1
        }

        async with session.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=120) as response:
            response.raise_for_status()
            result = await response.json()
            content = result['choices'][0]['message']['content']
            # content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
            return {
                "query": query,
                "content": content,
                "citations": result.get('citations', [])
            }

    except Exception as e:
        logger.error(f"Perplexity search failed for query '{query}': {str(e)}")
        return {"query": query, "content": f"Search Error: {str(e)}", "citations": []}

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
    
    prompt = """You need to break down the content in the discussion of research topic before into detailed sub-questions and generate 1 to 3 detail search queries for each sub-question.
    Keywords like "2024" or "launch date" should be avoided.
    Response format:
    {
        "sub_questions": [
            {
                "question": "detailed describe the research goal of the sub_question, and the expectation of what you want to get from the search",
                "query": ["Search query with detailed describe"]
            }
        ]
    }"""
    
    response = call_openrouter(
        prompt=f"{prompt}\nResearch topic:{query}",
        history=history,
        model=ANALYSIS_MODEL
    )
    try:
        json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON block found in response")
            
        json_str = json_match.group(1)
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Failed to parse analysis response: {str(e)}")
        logger.error(f"Problematic response: {response}")
        return {"sub_questions": []} 

async def execute_dynamic_search(sub_question: Dict, history: List[Dict], main_goal) -> Dict:
    """Asyncronously execute dynamic search process (integrated result saving)"""

    search_queue = deque(sub_question["query"])
    processed = set()
    results = []

    async with aiohttp.ClientSession() as session:
        for depth in range(MAX_SEARCH_DEPTH + 1):
            current_results = []
            tasks = []

            while search_queue:
                query = search_queue.popleft()
                if query in processed:
                    continue

                print(f"Searching [{sub_question['question']}] - {query}")
                tasks.append(call_perplexity_async(session, query))
                processed.add(query)

            api_responses = await asyncio.gather(*tasks)
            for response in api_responses:
                 save_search_result(response["query"], response)
                 current_results.append(response["content"])
                 

            if depth < MAX_SEARCH_DEPTH and current_results:
                analysis_prompt = f"""The main goal of the research is {main_goal}.
                ## Sub Question:{sub_question['question']}
                Synthesize the following results:
                ## Current Search Results:
                {current_results}
                please generate:
                1. Statement of supplementary search directions needed
                2. New 1 to 3 search queries based on the statement of suplementary search directions needed, with concisely and detailed describe.
                Respond according to the following JSON format:
                ```json
                {{
                    "missing_info": Statement of supplementary search directions needed,
                    "new_query": ["New Search query"]
                }}
                ```"""
                analysis_response = call_openrouter(analysis_prompt, history, ANALYSIS_MODEL)
                json_match = re.search(r'```json\n(.*?)\n```', analysis_response, re.DOTALL)

                if json_match:
                    json_string = json_match.group(1).strip()
                    try:
                        analysis = json.loads(json_string)
                        if "new_query" in analysis:
                            print(f"\n{analysis.get('missing_info', None)} \nAdd supplementary search: {analysis['new_query']}\n")
                            search_queue.extend(analysis["new_query"])
                        else:
                            print(f"\nNo supplementary search needed\n")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSONDecodeError: {e}")
                        logger.error(f"Problematic JSON string: {json_string}")
                        analysis = {"new_query": []}
                else:
                    logger.error("No JSON block found in analysis_response.")
                    analysis = {"new_query": []}
                    logger.error(f"Full analysis_response: {analysis_response}")

            results.extend(current_results)
            if not search_queue:
                break
    return results

def generate_research_report(main_goal: List[Dict]) -> str:
    """Generate the final research report (integrated processed content)"""

    try:
        processed_content = process_citations()
        prompt = """According to the conversation histories between user and assistant, merge the content from all search results, add appropriate text paragraphs, and expand it into an in-depth research report covering all search data. The report must mention all search results. The report should be persuasive, explain the cause and effect relationships.
                Each important argument or data should be accompanied by the corresponding citation number, e.g.: [1][2]. Ensure the citation format is correct and accurate, while ordinary descriptions do not need to be cited; at the end of the report, list all the references you have used above in an ordered list."""
        return call_openrouter(
            prompt=prompt + "\n" + processed_content,
            history=main_goal,
            model=WRITING_MODEL
        )
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        return "# Research Report\nGeneration failed due to internal error"
    
def organize_search_results(search_results: List[Dict]) -> str:
    """Organize all the search results in the same sub-question"""
    return

def main_flow():
    
    if not (PERPLEXITY_API_KEY or OPENROUTER_API_KEY):
        logger.error("Please set the environment variables PERPLEXITY_API_KEY and OPENROUTER_API_KEY.")
        return

    system_prompt = f"""You are a professional research assistant responsible for assisting users in conducting in-depth research.
                        Current date: {date.today()}
                        You need to conduct research direction discussions, task analysis, dynamic search, and generate a final report based on the user's research topic.
                        1. Research direction discussion: Determine research goals, key aspects to explore and important themes, research depth, and research scope with the user.
                        2. Task analysis: Decompose the research direction discussed earlier into specific research tasks and generate specific research questions.
                        3. Analyze and comment on the current status of the research question to see if there is any content that needs to be supplemented.
                        4. Generate research report: Based on the previous research results and discussions, generate an in-depth research report that meets user expectations."""
    conversation_history = [{"role": "system", "content": system_prompt}]
    
    try:
        user_query = input("\nPlease enter the research topic: ")

        if input("Need initial search? (y/n)").lower() == "y":
            print("\n===Performing initial search===")

            async def get_initial_search():
                async with aiohttp.ClientSession() as session:
                    return await call_perplexity_async(session, user_query, "sonar")
            
            init_search_result = asyncio.run(get_initial_search())
            init_search = init_search_result['content']
            user_prompt = f"""Discuss the research direction with the user and correct.
                        This is the initial search result for this research topic, 
                        which gives you some preliminary understanding of the topic to propose the correct research direction: {init_search}
                        This is the research topic and content that the user wants: {user_query}
                        List the questions you need to ask the user in the end, and keep update the research plan in every conversation."""
        else:
            user_prompt = f"""Discuss the research direction with the user and correct.
                        This is the research topic and content that the user wants: {user_query}
                        List the questions you need to ask the user in the end, and keep update the research plan in every conversation."""
        print("\n" + call_openrouter(user_prompt, conversation_history))
        while True:
            comfirmation = input("Anything you want to change? (y/n)").lower()
            if comfirmation == "y":
                user_query = input("Please enter your thoughts: ")
                print("\n" + call_openrouter(user_query, conversation_history) + "\n")
            else:
                break
        print("\n")
        main_goal = list(conversation_history[-1])
        
        # Task Analysis Stage
        print("===Analyzing research tasks===")
        task_plan = analyze_task(user_query, conversation_history)
        print(json.dumps(task_plan, indent=4))
        
        num_sub_questions = len(task_plan["sub_questions"])
        print(f"\nTotal number of sub-questions: {num_sub_questions}")
        
        # Dynamic Search Stage
        print("\n===Starting to execute in-depth search===")
        for i, sub in enumerate(task_plan["sub_questions"]):
            print(f"\n=== Searching sub-question {i+1} of {num_sub_questions} ===")
            asyncio.run(execute_dynamic_search(sub, conversation_history, main_goal))
        
        # Generate Final Report
        print("\n===Generating research report===")
        report = generate_research_report(main_goal)
        
        # Save Results
        with open("research_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to: research_report.md")
        
    except Exception as e:
        logger.error(f"Process execution failed:{str(e)}")

if __name__ == "__main__":
    # Clear old files during initialization
    if os.path.exists(SEARCH_RESULTS_FILE):
        os.remove(SEARCH_RESULTS_FILE)
    if os.path.exists(RESEARCH_REPORT_FILE):
        os.remove(RESEARCH_REPORT_FILE)
    if os.path.exists(SEARCH_RESULT_FILE_WITH_GLOBAL_CITATIONS):
        os.remove(SEARCH_RESULT_FILE_WITH_GLOBAL_CITATIONS)
    
    main_flow()