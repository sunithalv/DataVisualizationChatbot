import streamlit as st
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from dataviz.graphbuilder import build_graph
from dataviz.logging import logger
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="AI SQL Assistant", page_icon="🤖", layout="wide")

st.title("🤖 AI SQL Assistant")
   
streamlit_callback = StreamlitCallbackHandler(st.container())


st.markdown("---")
st.subheader("About")
st.info("This AI SQL Assistant provides answers or visualizations for your data . Ask questions in plain English, and get SQL-powered answers!")

st.header("Chat Interface")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_query = st.chat_input(placeholder="Ask anything from the database")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        response_container = st.container()
        with response_container:
            graph=build_graph()
            response=None
            for step in graph.stream(
                {"question": user_query}
            ):
                logger.info(f"Output of step {step}") 
                if 'generate_answer' in step:
                    response = step['generate_answer']['answer']
                elif 'get_visualization' in step:
                    response = step['get_visualization']['answer']
            response_container.markdown(response)
        
            st.session_state.messages.append({"role": "assistant", "content": response})
            



    