from datetime import timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
    'start_date': days_ago(2),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'my_first_dag',
    default_args=default_args,
    description='A simple DAG',
    schedule_interval=timedelta(days=1),
    catchup=False,
) as dag:

    t1 = DummyOperator(
        task_id='task_1',
    )

    t2 = DummyOperator(
        task_id='task_2',
    )

    t1 >> t2
