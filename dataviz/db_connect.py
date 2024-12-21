#import streamlit as st
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
load_dotenv()

#@st.cache_resource(ttl="2h")
def configure_db():
    project=os.getenv('GOOGLE_PROJECT')
    dataset=os.getenv('BIGQUERY_DATASET')
    service_account_file=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    sql_url = (
        f"bigquery://{project}/{dataset}?credentials_path={service_account_file}"
    )
    return SQLDatabase.from_uri(sql_url)
 