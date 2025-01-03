from langchain_openai import ChatOpenAI
from dataviz.db_connect import configure_db
from dataviz.prompts import get_prompt_template,create_data_transform_prompt
from typing_extensions import TypedDict,Annotated
from langchain_community.tools import QuerySQLDataBaseTool
from langgraph.graph import START, StateGraph,END
from langchain_core.runnables.base import RunnableLambda
import pandas as pd
import streamlit as st
import altair as alt
import json


llm = ChatOpenAI(model_name="gpt-4o-mini", streaming=True)

db = configure_db()

query_prompt_template=get_prompt_template()

class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str
    chart_type:str
    viz_data:str
    chart:dict

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
            "top_k": 30,
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

def parse_response_to_dict(response: str) -> dict:
    """
    Parse the response string into a dictionary with 'Recommended Visualization' and 'Reason' keys.
    
    :param response: The response string to parse.
    :return: A dictionary with parsed values.
    """
    lines = response.strip().split("\n")
    response_dict = {}

    for line in lines:
        if line.startswith("Recommended Visualization:"):
            response_dict["Recommended Visualization"] = line.replace("Recommended Visualization:", "").strip()
        elif line.startswith("Reason:"):
            response_dict["Reason"] = line.replace("Reason:", "").strip()
    
    return response_dict

#Generate visualization
def get_visualization(state: State):
    """Returns recommended visualization or charts using retrieved information as context."""
    viz_prompt = f"""
    You are an AI assistant that recommends appropriate data visualizations for price,count,size,colour,brand distribution and analysis for t shirts in a store.
    Based on the user's question, SQL query, and query results, suggest the most suitable type of graph or chart to visualize the data.

    Available chart types and their best use cases:

    - Bar Graphs (for 3+ categories): 
    * Comparing distributions or counts across multiple categories such as size, colour or brand
    * Average discount percentage or effectiveness by brand.
    
    - Stacked Bar Chart: 
    * Stock quantity by brand,size or color, grouped by size,color or brand.                                       

    - Histogram:
    * Distribution of discount percentages or t shirt prices.
      Note: Total should sum to 100%
                                              
    - Scatter Plots (for numeric relationships):
    * T-shirt price vs. discount percentage to see how discounts vary with price of t shirts
    * Stock quantity vs. discount percentage to identify trends (e.g., are high-stock items discounted more?).
    * Price vs. stock quantity to see if cheaper t-shirts have higher stock.                                         
    Note: Both axes must be numeric, non-categorical
    
    - Pie chart
    * Proportion of stock contributed by each brand or color.
                                              
    Special Cases:
    Raw Data:
    * Individual records → No chart (tabular display)
    * Non-aggregated data → No chart (tabular display)

    Tables in scope:
    - t_shirts: t_shirt_id, brand, color, size, price, stock_quantity
    - discounts: discount_id, t_shirt_id, pct_discount

    Question: {state["question"]}
    SQL Query: {state["query"]}
    SQL Result: {state["result"]}

    Provide your response in the following format:
    Recommended Visualization: [Chart type or "none"]. ONLY use the following names: bar, stacked bar, histogram, pie, scatter.
    Reason: [Brief explanation for your recommendation]
    """

    response = llm.invoke(viz_prompt)
    # Update the state with the response_dict
    state["answer"] = response.content  # Explicitly store it in state
    return state

#@RunnableLambda
def transform_data_for_visualization_chain(state:State):
     try:
         answer=state.get("answer")
         response_dict = parse_response_to_dict(answer)
         print("State in transform_data_for_visualization_chain:", state)
         chart_type = response_dict.get("Recommended Visualization")
         print("Chart type in transform_data_for_visualization_chain:", chart_type)
         #return response_dict
         result = state.get("result")
         if not chart_type or not result:
            return {"viz_data": None}
        
         if chart_type == 'none':
            transform_prompt = None
         else:
            transform_prompt=create_data_transform_prompt(chart_type.lower(),result,state.get("question"))
            print("Transform Prompt in transform_data_for_visualization_chain:", transform_prompt)

         assign_chart_type_and_result = RunnableLambda(
            lambda args: {**args, "chart_type": chart_type, "result": result}
         )

         if transform_prompt:
            transform_chain = (
                assign_chart_type_and_result
                | transform_prompt
                | llm
            )
            response=transform_chain.invoke(state)
            print("Response in transform_data_for_visualization_chain:", response)
            return {'viz_data':response.content,'chart_type':chart_type}

         return {"viz_data": None}

     except Exception as e:
        print(e)
        print(f"Error in transform_data_for_visualization: {e}")
        return {"viz_data": None}
          
   
def get_flow(state:State):
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
        lambda state: get_flow(state)  # Only valid nodes: "generate_answer" or "get_visualization"
    )
    graph_builder.add_node("generate_answer", generate_answer)
    graph_builder.add_edge("generate_answer", END)

    # Explicitly define the visualization sequence and its connection
    graph_builder.add_node("get_visualization", get_visualization)
    graph_builder.add_node("transform_data_for_visualization_chain", transform_data_for_visualization_chain)
    graph_builder.add_edge("get_visualization", "transform_data_for_visualization_chain")
    graph_builder.add_edge("transform_data_for_visualization_chain", END)
    graph = graph_builder.compile()
    return graph


