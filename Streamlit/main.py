import streamlit as st
import os
from google.cloud import storage
from google.oauth2 import service_account
import tempfile
import pymysql

#Util functions
def database_conn():
    try:  
        conn = pymysql.connect(
                ##add to .env
                host = st.secrets["host"], 
                user = st.secrets["user"],
                password = st.secrets["password"],
                db = st.secrets["db"])
        cursor = conn.cursor()
        return conn,cursor
    except Exception as error:
        print("Failed to connect to database {}".format(error))
        
def query_database(query):
    try:  
        _,cursor=database_conn()
        cursor.execute(query)
        return cursor
    except Exception as error:
        print("Failed to query record from table {}".format(error))

def get_processed_recording_name():              
    result=query_database("SELECT DISTINCT Recording_Name FROM Recording_Details")
    recording_names=[]
    for row in result:
        recording_names.append((row))
    return recording_names

def get_selected_questions(recording_name,index):
    if index == 0:
        col='Question1'
    elif index == 1:
        col='Question2'
    elif index == 2:
        col='Question3'
    else:
        col='Question4'
    try:  
        _,cursor=database_conn()
        sql_query = "SELECT {} FROM Recording_Details WHERE Recording_Name = %s".format(col)
        cursor.execute(sql_query, (recording_name,))
        result = cursor.fetchone()
        return result[0]
    except Exception as error:
        print("Failed to query questions from table {}".format(error))

with st.form("Upload_form", clear_on_submit=True):
        uploaded_file=st.file_uploader("Choose an audio file",type=['mp3','m4a','wav'],accept_multiple_files=False)
        submitted = st.form_submit_button("Upload Recording")
        if submitted:
            with st.spinner('Wait for it...'):
                if uploaded_file is not None:
                    # Create API client.
                    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
                    storage_client = storage.Client(credentials=credentials)
                    #os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "big_data_pipeline_cred.json"
                    #storage_client = storage.Client()
                    bucket = storage_client.get_bucket(st.secrets["bucket_name"])
                    
                    # Save uploaded file to a temporary file
                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_file.flush()
                        os.fsync(tmp_file.fileno())
                        
                        # Upload the temporary file to Cloud Storage
                        blob = bucket.blob(f"recording/{uploaded_file.name}")
                        blob.upload_from_filename(tmp_file.name)
                        
                    # Delete the temporary file
                    os.unlink(tmp_file.name)
                st.success('Recording uploaded successfully!')

option = st.selectbox(
    'Select the recording you want to analyze',
    (recording_name[0] for recording_name in get_processed_recording_name()))

st.write('You selected:', option)

question_options= ("Q1. What is the summary of the audio file?" , "Q2. What is the emotion in the recording?" , "Q4. What are the keywords in the recording?" ,"Q5. What could be the next possible steps?")
question_dropdown = st.selectbox(
    'Select the question',question_options)
selected_index= question_options.index(question_dropdown)

if st.button("Query for answer?"):
    st.write(get_selected_questions(option,selected_index))