from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime

default_args = {
    'start_date': datetime(2023, 3, 29),
    'retries': 1,
}

dag = DAG('install_ffmpeg',
          default_args=default_args,
          schedule_interval=None)

install_ffmpeg = BashOperator(
    task_id='install_ffmpeg',
    bash_command='sudo apt-get update && sudo apt-get -y install ffmpeg',
    dag=dag)
