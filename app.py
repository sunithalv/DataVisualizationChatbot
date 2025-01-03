import streamlit as st
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from dataviz.graphbuilder import build_graph
from dataviz.utils import display_visualization,download_chart_as_html
from dataviz.logging import logger
import io
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Store SQL Assistant", page_icon="🤖", layout="wide")

st.title("🤖 Store SQL Assistant")
   
streamlit_callback = StreamlitCallbackHandler(st.container())
st.subheader("About")
st.info("This SQL Assistant provides answers or visualizations for your store data . Ask questions in plain English, and get SQL-powered answers!")
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]


# Render chat history from st.session_state
if "messages" in st.session_state:
    for message in st.session_state.messages:
        if message["role"] == "assistant":
                if "chart" in message:
                    with st.container():  # Use a container instead of st.chat_message
                        # Display the heading in the middle (centered, bold)
                        chart_label = message["content"]
                        chart=message["chart"]
                        st.plotly_chart(chart, use_container_width=True)
                        st.download_button(
                            label="Download Chart as HTML",
                            data=download_chart_as_html(chart),
                            file_name=f"{chart_label}_chart.html",
                            mime="text/html"
                        )
                else:
                    # Display the assistant's response
                    with st.chat_message("assistant"):  # Use st.chat_message for assistant
                        st.markdown(message["content"])

        elif message["role"] == "user":
            # Display the user's query
            with st.chat_message("user"):  # Use st.chat_message for user
                st.markdown(message["content"])


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
                    response_container.markdown(response)
                    st.session_state.messages.append({
                    "role": "assistant",
                    "content": response  # Append text response
                    })
                elif 'get_visualization' in step:
                    response = step['get_visualization']['answer']
                    response_container.markdown(response) 
                    st.session_state.messages.append({
                    "role": "assistant",
                    "content": response  # Append text response
                    }) 
                elif 'transform_data_for_visualization_chain' in step:
                    viz_data=step['transform_data_for_visualization_chain']['viz_data']
                    chart_type=step['transform_data_for_visualization_chain']['chart_type']
                    chart,chart_label=display_visualization(viz_data,chart_type)
                    
                    st.download_button(
                        label="Download Chart as HTML",
                        data=download_chart_as_html(chart),
                        file_name=f"{chart_label}_chart.html",
                        mime="text/html"
                    )

                    # Append chart to session state messages
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": chart_label,  # Placeholder for text description
                        "chart": chart  # Store the chart object
                    })
 


            



    