from google.cloud import storage
import os
import openai
import pymysql
from dotenv import load_dotenv
from pydub import AudioSegment


load_dotenv()

openai.api_key = os.getenv("open_api_key")

#Utils
def init_gcp_bucket():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="big_data_pipeline_cred.json"
    storage_client = storage.Client()
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
        os.remove(f"{Recording_Name}.txt")
    except Exception as error:
        print("Failed to insert record into table {}".format(error))
def convert_to_wav(file_path):
    # load the audio file
    audio = AudioSegment.from_file(file_path)

    # export the audio file as WAV
    file_path_wav = f"{file_path[:-4]}.wav"
    audio.export(file_path_wav, format="wav")

    return file_path_wav  
## Task 1
def get_recordings_objects(recording_name):
        storage_client=init_gcp_bucket()
        bucket = storage_client.get_bucket(os.getenv("bucket_name"))
        blob_name = f"recording/{recording_name}.mp3"
        blob=bucket.blob(blob_name)
        blob.download_to_filename("recording.mp3")

def transcribe_audio(file_path,file="recording.mp3"):
    # Convert the MP3 file to WAV format
    sound = AudioSegment.from_mp3(file)
    sound.export('/tmp/audio.wav', format= 'wav')
    model_id = 'whisper-1'
    with open('/tmp/audio.wav','rb') as audio_file:
        transcription=openai. Audio. transcribe(api_key=openai.api_key, model=model_id, file=audio_file, response_format='text')
    file_text = open(f"{file_path}.txt", "w")
    file_text.write(transcription)
    return transcription
    # ti.con_push(key="response", value=response)

## Task 3
def upload_transcripts(file_name):
    # #Upload transcribe file
    upload_objects(f"transcript/{str(file_name)}",file_name)

## Task 4
def query_chat_gpt(query,prompt):
    #prompt=get_transcripts_objects(file_name)
    response_summary =  openai.ChatCompletion.create(
        model = "gpt-3.5-turbo", 
        messages = [
            {"role" : "user", "content" : f'{query} {prompt}'}
        ]
    )
    summary = response_summary['choices'][0]['message']['content']
    return summary
    
    
#Checking Execution
get_recordings_objects("Believer")#1
transcribed=transcribe_audio("Believer")#2
print(transcribed)
upload_transcripts("Believer.txt")#3
#4
q1=query_chat_gpt("give the summary in 800 character: ",transcribed )
q2=query_chat_gpt("what is the mood or emotion in the text not more than 800 character? ",transcribed)
q3=query_chat_gpt("what are the main keywords not more than 800 character? ",transcribed)
q4=query_chat_gpt("What should be the next steps not more than 800 character?",transcribed)
write_database("Believer",q1,q2,q3,q4)


# with DAG(dag_id="OpenAI_Operations_dag",
#         start_date=datetime(2023,3,28),
#         schedule_interval="@hourly"
#         ) as dag:
#         task1= PythonOperator(
            
#         )
#         task1=PythonOperator(
#             task_id = "wisper_api",
#             python_callable = transcribe_audio,
#             params ={"file" : {link}}
#         )
        
# task1
