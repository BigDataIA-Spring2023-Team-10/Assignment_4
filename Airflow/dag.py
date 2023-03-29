from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from google.cloud import storage
from google.oauth2 import service_account
import os
import pymysql
import whisper
import openai
from pydub import AudioSegment
import pendulum
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.hooks.base_hook import BaseHook
from google.auth.credentials import AnonymousCredentials

openai.api_key = os.getenv("open_api_key")
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 3, 28),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


dag = DAG(
    'short_song_transcription',
    default_args=default_args,
    description='Transcription of short song recording',
    schedule_interval=timedelta(days=1),
    catchup=False
)

#Util functions
# def init_gcp_bucket():
#     os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="big_data_pipeline_cred.json"
#     storage_client = storage.Client()
#     return storage_client

# def init_gcp_bucket():
#     credentials = BaseHook.get_connection("my_gcp_creds").extra_dejson
#     creds = None
    
#     # Check if credentials are provided and not empty
#     if credentials:
#         creds = credentials.get("keyfile_path")

#     # Use Google Application Default Credentials (ADC) if no credentials are provided
#     storage_client = storage.Client.from_service_account_json(creds) if creds else storage.Client(
#         credentials=AnonymousCredentials()
#     )
    
#     return storage_client

# def init_gcp_bucket():
#     # Get the credentials from Airflow Admin Connection
#     credentials = BaseHook.get_connection("my_gcp_creds").extra_dejson
    
#     # Set the credentials
#     storage_client = storage.Client(credentials=credentials)
#     return storage_client

def init_gcp_bucket():
    # Get the credentials from Airflow Admin Connection'
    your_gcp_keys = { 
        "type": os.environ.get('type'),
        "project_id": os.environ.get('project_id'),
        "private_key_id": os.environ.get('private_key_id'),
        "private_key": os.environ.get('private_key').replace('\\n', '\n'),
        "client_email": os.environ.get('client_email'),
        "client_id": os.environ.get('client_id'),
        "auth_uri": os.environ.get('auth_uri'),
        "token_uri": os.environ.get('token_uri'),
        "auth_provider_x509_cert_url": os.environ.get('auth_provider_x509_cert_url'),
        "client_x509_cert_url": os.environ.get('client_x509_cert_url')
    }
    # gcp_hook = GoogleCloudBaseHook(gcp_conn_id='my_gcp_creds')
    # credentials = gcp_hook._get_credentials()
    
    # Set the credentials
    credentials = service_account.Credentials.from_service_account_info(your_gcp_keys)
    storage_client = storage.Client(credentials=credentials)
    return storage_client

def upload_objects(folder,object):
    storage_client=init_gcp_bucket()
    bucket = storage_client.get_bucket(os.getenv("bucket_name")) 
    blob = bucket.blob(folder)
    blob.upload_from_filename(object)

def get_transcripts_objects(file_name):
    storage_client=init_gcp_bucket()
    bucket = storage_client.get_bucket(os.getenv("bucket_name")) 
    blob_name = f"transcript/{file_name}.txt"
    blob=bucket.blob(blob_name)
    return blob.download_as_string()

def write_database(Recording_Name,Q1,Q2,Q3,Q4):
    try:  
        conn = pymysql.connect(
                host = os.getenv("host"), 
                user = os.getenv("user"),
                password = os.getenv("password"),
                db = os.getenv("db"))
        cursor = conn.cursor()
        sql_insert=f"INSERT INTO Recording_Details ( Recording_Name , Question1 , Question2, Question3,Question4) VALUES (%s, %s ,%s, %s, %s);"
        record=(Recording_Name,Q1,Q2,Q3,Q4)
        cursor.execute(sql_insert,record)
        conn.commit()
        cursor.close()
        os.remove("recording.mp3")
        os.remove("Short_song.txt")
    except Exception as error:
        print("Failed to insert record into table {}".format(error))
 
        
def get_recordings_objects(recording_name):
    storage_client=init_gcp_bucket()
    bucket = storage_client.get_bucket(os.getenv("bucket_name"))
    blob_name = f"recording/{recording_name}.mp3"
    blob=bucket.blob(blob_name)
    blob.download_to_filename("recording.mp3")


def transcribe_audio(file_path,file="recording.mp3"):
    # Convert the MP3 file to WAV format
    os.environ["PATH"] += os.pathsep + '/usr/bin/ffmpeg'
    sound = AudioSegment.from_mp3(file)
    sound.export('/tmp/audio.wav', format= 'wav')
    model_id = 'whisper-1'
    with open('/tmp/audio.wav','rb') as audio_file:
        transcription=openai.Audio.transcribe(api_key=openai.api_key, model=model_id, file=audio_file, response_format='text')
        file_text = open(f"{file_path}.txt", "w")
        file_text.write(transcription)
        return transcription
    # model = whisper.load_model("tiny")
    # transcribed_audio = model.transcribe(file)
    # file_text = open(f"{file_path}.txt", "w")
    # file_text.write(transcribed_audio['text'])
    # return transcribed_audio['text']

def chat_gpt(query,prompt):
    response_summary =  openai.ChatCompletion.create(
        model = "gpt-3.5-turbo", 
        messages = [
            {"role" : "user", "content" : f'{query} {prompt}'}
        ]
    )
    return response_summary['choices'][0]['message']['content']
    
def query_chat_gpt(prompt):
    #Query1
    query1='give the summary in 1000 character: '
    q1=chat_gpt(prompt,query1)
    ##Query2
    query2="what is the mood or emotion in the text not more than 1000 character? "
    q2=chat_gpt(prompt,query2)
    ##Query3
    query3="what are the main keywords not more than 1000 character? "
    q3=chat_gpt(prompt,query3)
    ##Query4
    query4="What should be the next steps not more than 1000 character?"
    q4=chat_gpt(prompt,query4)
    write_database("Short_song",q1,q2,q3,q4)

# t0 = BashOperator(
#     task_id='install_dependencies',
#     bash_command='pip install -r ./requirements.txt',
#     dag=dag
# )

t1 = PythonOperator(
    task_id='download_recording',
    python_callable=get_recordings_objects,
    op_kwargs={'recording_name': 'Short_song'},
    dag=dag,
    provide_context=True,
)

t2 = PythonOperator(
    task_id='transcribe_audio',
    python_callable=transcribe_audio,
    op_kwargs={'file_path': 'Short_song'},
    dag=dag,
    provide_context=True,
)

t3 = PythonOperator(
    task_id='upload_transcript',
    python_callable=upload_objects,
    op_kwargs={'folder': 'transcript/Short_song.txt', 'object': 'Short_song.txt'},
    dag=dag,
    provide_context=True,
)

t4 = PythonOperator(
    task_id='query_chat_gpt',
    python_callable=query_chat_gpt,
    op_kwargs={'prompt': get_transcripts_objects('Short_song')},
    dag=dag,
    provide_context=True,
)


t1 >> t2 >> t3 >> t4