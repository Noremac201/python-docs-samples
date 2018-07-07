# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An example DAG demonstrating Kubernetes Pod Operator."""

from __future__ import print_function

import datetime

from airflow import models
from airflow.contrib.kubernetes.pod import Resources
from airflow.contrib.kubernetes.secret import Secret
from airflow.contrib.kubernetes.volume import Volume
from airflow.contrib.kubernetes.volume_mount import VolumeMount
from airflow.contrib.operators import kubernetes_pod_operator

default_dag_args = {
    # Continue to run this DAG once per day
    'schedule_interval': datetime.timedelta(days=1),
    # Setting start date as yesterday starts the DAG immediately after discovery
    'start_date': datetime.datetime.now() - datetime.timedelta(days=1)
}

# A Secret is an object that contains a small amount of sensitive data
# such as a password, a token, or a key. Such information might otherwise be
# put in a Pod specification or in an image; putting it in a Secret object
# allows for more control over how it is used, and reduces the risk of
# accidental exposure.
secret_file = Secret(
    # Mounts the secret as a file in RAM-backed tmpfs
    deploy_type='volume',
    # File path of where to deploy the target, since 'volume'
    deploy_target='/etc/sql_conn',
    # Name of secret in Kubernetes
    secret='airflow-secrets',
    # Key of the secret within Kubernetes
    key='sql_alchemy_conn'
)

secret_env = Secret(
    # Exposes secret as environment variable
    deploy_type='env',
    # The environment variable the secret is specified under
    deploy_target='SQL_CONN',
    # Name of secret in Kubernetes
    secret='airflow-secrets',
    # Key of the secret within Kubernetes
    key='sql_alchemy_conn'
)

resources_obj = Resources(
    # Amount of memory requested, can use E, P, T, G, M, K, Ei, Pi,
    # Ti, Gi, Mi, Ki as suffixes
    request_memory='200Mi',
    # Tells container to attempt to use specified number of cpus. One 'cpu' is
    # equivalent to 1 AWS vCPU, 1 GCP Core, 1 Azure vCore or 1 Hyperthread on
    # a bare-metal intel processor with Hyperthreading
    # If CPU request exceeds all of your node's capacities it will fail to ever
    # get scheduled.
    request_cpu='2',
    # If memory limit is exceeded the Pod goes up for termination, if no
    # limit is specified there is no upper bound on the amount of memory it can
    # use. You can also specify a default memory limit on a per-namespace basis
    limit_memory='100Mi',
    # If cpu request exceeds your node's capacity, it will fail to ever get
    # scheduled. The m suffix stands for milli-cpus, therefore .5 cpu and 500m
    # cpu are equivalent.
    limit_cpu='500m'
)

# Creates a volume of type emptyDir without any configs
volumes = [Volume(name='empty-vol', configs={'emptyDir', {}})]

# Used to mount pod level volumes to a running container
volume_mounts = [VolumeMount(name='test-vol-mount',
                             mount_path='/root/mount_file',
                             sub_path='None',
                             read_only=False)
                ]

# Any task you create within the context manager is automatically added to the
# DAG object.
with models.DAG(dag_id='kubernetes-example',
                default_args=default_dag_args) as dag:
  # Only name, namespace, and image are required to create a
  # KubernetesPodOperator. This operator defaults to using the config file found
  # at `~/.kube/config` if no `config_file` parameter is specified.
  kubernetes_min_pod = kubernetes_pod_operator.KubernetesPodOperator(
      # The ID specified for the task
      task_id='pi_task_full',
      # Name of task you want to run, used to generate pod id
      name='pi',
      # The namespace to run within Kubernetes
      # To reduce resource starvation for airflow workers and scheduler in
      # Cloud Composer, be sure to have namespace point to a custom node pool
      namespace='default',
      # Docker image specified. Defaults to hub.docker.com, but any fully
      # qualified URLs will point to a custom repository
      image='ubuntu',
  )

  kubernetes_full_pod = kubernetes_pod_operator.KubernetesPodOperator(
      task_id='pi_task_full',
      name='pi',
      namespace='default',
      image='perl',
      # Entrypoint of the container, if not specified the Docker container's
      # entrypoint is used.
      cmds=['perl'],
      # Arguments to the entrypoint. The docker image's CMD is used if this is
      # not provided
      arguments=['-Mbignum=bpi', '-wle', 'print bpi(2000)'],
      # The secrets to pass to Pod
      secrets=[secret_env, secret_file],
      # Labels to apply to the Pod
      labels={'pod-label': 'label-name'},
      # Timeout to start up the pod, default is 120
      startup_timeout_seconds=120,
      # The environment variables to be initialized in the container
      env_vars={'EXAMPLE_VAR': '/example/value'},
      # If true, logs stdout output of container
      get_logs=True,
      # Determines when to pull a fresh image, if 'IfNotPresent' will cause the
      # Kubelet to skip pulling an image if it already exists. If you want to
      # always pull a new image, set it to 'Always'
      image_pull_policy='IfNotPresent',
      # Annotations are non-identifying metadata you can attach to the Pod
      # Can be a large range of data, and can include characters
      # that are not permitted by labels
      annotations={'key1': 'value1'},
      # Resource specifications for Pod, of type pod.Resource
      resources=resources_obj,
      # Specifies path to kubernetes config. If no config is specified will
      # default to '~/.kube/config'
      config_file='~/.kube/config',
      # If true, the content of /airflow/xcom/return.json from container will
      # also be pushed to an XCom when the container ends
      xcom_push=True,
      # List of volumes to pass to the Pod
      volumes=volumes,
      # list of volume mounts to pass to the Pod
      volume_mounts=volume_mounts,
      # Affinity determines which nodes the Pod can run on based on the config
      # For more information see
      # https://kubernetes.io/docs/concepts/configuration/assign-pod-node/
      affinity={}
  )
