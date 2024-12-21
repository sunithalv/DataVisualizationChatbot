from langchain_openai import ChatOpenAI
from dataviz.db_connect import configure_db
from dataviz.prompts import get_prompt_template
from typing_extensions import TypedDict,Annotated
from langchain_community.tools import QuerySQLDataBaseTool
from langgraph.graph import START, StateGraph,END


llm = ChatOpenAI(model_name="gpt-4o-mini", streaming=True)

db = configure_db()

query_prompt_template=get_prompt_template()

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str

#A TypedDict that specifies the expected structure of the output.
#query: A field of type str, annotated to indicate that it should contain a syntactically valid SQL query.
class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]


#generate an SQL query by interacting with an LLM and return it in a structured format
def write_query(state: State):
    """Generate SQL query to fetch information."""
    prompt = query_prompt_template.invoke(
        {
            "dialect": db.dialect,
            "top_k": 10,
            "table_info": db.get_table_info(),
            "input": state["question"],
        }
    )
    #Configures the LLM to return its results as a QueryOutput structure, ensuring compliance with the expected format
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    print(result)
    return {"query": result["query"]}

def execute_query(state: State):
    """Execute SQL query."""
    execute_query_tool = QuerySQLDataBaseTool(db=db)
    return {"result": execute_query_tool.invoke(state["query"])}

#Generate answer
def generate_answer(state: State):
    """Answer question using retrieved information as context."""
    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, answer the user question.\n\n"
        f'Question: {state["question"]}\n'
        f'SQL Query: {state["query"]}\n'
        f'SQL Result: {state["result"]}'
    )
    response = llm.invoke(prompt)
    return {"answer": response.content}

#Generate visualization
def get_visualization(state: State):
    """Returns recommended visualization or charts using retrieved information as context."""
    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, recommend a visualization chart like bar chart,pie chart,scatter plot etc.\n\n"
        f'Question: {state["question"]}\n'
        f'SQL Query: {state["query"]}\n'
        f'SQL Result: {state["result"]}'
    )
    response = llm.invoke(prompt)
    return {"answer": response.content}

def get_flow(state):
    """
    Determines whether to go to 'generate_answer' or 'get_visualization'
    based on the user query stored in the state.

    Args:
        state (dict): The current state containing the user query.

    Returns:
        str: The next node ('generate_answer' or 'get_visualization').
    """
    # Extract the user query from the state
    user_query = state.get("question", "")

    # Example condition: Check for keywords in the query
    visualization_keywords = ["chart", "graph", "visualize", "plot", "diagram"]

    # Check if the query contains visualization-related keywords
    if any(keyword in user_query.lower() for keyword in visualization_keywords):
        return "get_visualization"

    # Default flow
    return "generate_answer"

def build_graph():
    graph_builder = StateGraph(State).add_sequence(
        [write_query, execute_query]
    )
    graph_builder.add_edge(START, "write_query")
    graph_builder.add_conditional_edges(
        "execute_query",
        get_flow
    )
    graph_builder.add_node("generate_answer",generate_answer)
    graph_builder.add_node("get_visualization",get_visualization)
    graph_builder.add_edge("generate_answer", END)
    graph_builder.add_edge("get_visualization", END)
    graph = graph_builder.compile()
    return graph
