from airflow import DAG
from airflow.providers.amazon.aws.operators.emr_create_job_flow import EmrCreateJobFlowOperator
from airflow.providers.amazon.aws.operators.emr_add_steps import EmrAddStepsOperator
from airflow.providers.amazon.aws.sensors.emr_step import EmrStepSensor
from airflow.providers.amazon.aws.operators.emr_terminate_job_flow import EmrTerminateJobFlowOperator
from airflow.models import Variable
from airflow.utils.dates import days_ago
from datetime import timedelta

DEFAULT_ARGS = {'owner': 'airflow'}


user = Variable.get('dev_db_user')
password = Variable.get('dev_db_password')
host = Variable.get('dev_db_host')


SPARK_STEPS = [
    {
        'Name': 'dev_dummy_job',
        'ActionOnFailure': 'CONTINUE',
        'HadoopJarStep': {
            'Jar': 'command-runner.jar',
            'Args': [
                "spark-submit",
                "--deploy-mode",
                "cluster"
                "--conf",
                f"spark.executorEnv.host={host}",
                "--conf",
                f"spark.executorEnv.user={user}",
                "--conf",
                f"spark.executorEnv.password={password}",
                "s3://airflow-temp-test-ap-se-1/dags/dev_dummy_job.py",
            ],
        },
    }
]

JOB_FLOW_OVERRIDES = {
    "Name": "dev_dummy_job",
    "ReleaseLabel": "emr-6.3.0",
    "Instances": {
        "InstanceGroups": [
            {
                "Name": "Primary node",
                "Market": "SPOT",
                "InstanceRole": "MASTER",
                "InstanceType": "m5.xlarge",
                "InstanceCount": 1,
            },
            {
                "Name": "Core nodes",
                "Market": "SPOT",
                "InstanceRole": "CORE",
                "InstanceType": "m5.xlarge",
                "InstanceCount": 1,
            },
        ],
        "KeepJobFlowAliveWhenNoSteps": False,
        "TerminationProtected": False,
    },
    "Steps": SPARK_STEPS,
    "JobFlowRole": "EMR_EC2_DefaultRole",
    "ServiceRole": "EMR_DefaultRole",
}

with DAG(
    'emr_job_flow_manual_steps_dag',
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=days_ago(1),
    schedule_interval='0 0 * * *',
    tags=['emr'],
) as dag:

    cluster_creator = EmrCreateJobFlowOperator(
        task_id='create_job_flow',
        job_flow_overrides=JOB_FLOW_OVERRIDES,
        aws_conn_id='aws_default',
        emr_conn_id='emr_default',
    )

    step_adder = EmrAddStepsOperator(
        task_id='add_steps',
        job_flow_id="{{ task_instance.xcom_pull('create_job_flow', key='return_value') }}",
        aws_conn_id='aws_default',
        steps=SPARK_STEPS,
    )

    step_checker = EmrStepSensor(
        task_id='watch_step',
        job_flow_id="{{ task_instance.xcom_pull('create_job_flow', key='return_value') }}",
        step_id="{{ task_instance.xcom_pull('add_steps', key='return_value')[0] }}",
        aws_conn_id='aws_default',
    )

    cluster_remover = EmrTerminateJobFlowOperator(
        task_id='remove_cluster',
        job_flow_id="{{ task_instance.xcom_pull('create_job_flow', key='return_value') }}",
        aws_conn_id='aws_default',
    )

    cluster_creator >> step_adder >> step_checker >> cluster_remover
