#!/usr/bin/env python3
import boto3
import sys
import subprocess
import os
import traceback
import logging
import datetime
import signal
import inquirer
import json
import string
from inquirer import themes
from inquirer.render.console import ConsoleRender, List
from readchar import key

# emacs風のキーバインド
class ExtendedConsoleRender(ConsoleRender):
    def render_factory(self, question_type):
        if question_type == "list":
            return ExtendedList
        return super().render_factory(question_type)

# CTRL_MAP["B"]はkey.CTRL_Bでも良いのだけれどAからZまで全部は定義されていなかったので
CTRL_MAP = {c: chr(i) for i, c in enumerate(string.ascii_uppercase, 1)}


class ExtendedList(List):
    def process_input(self, pressed):
        # emacs style
        if pressed in (CTRL_MAP["B"], CTRL_MAP["P"]):
            pressed = key.UP
        elif pressed in (CTRL_MAP["F"], CTRL_MAP["N"]):
            pressed = key.DOWN
        elif pressed == CTRL_MAP["G"]:
            pressed = CTRL_MAP["C"]
        elif pressed == CTRL_MAP["A"]:
            self.current = 0
            return
        elif pressed == CTRL_MAP["G"]:
            self.current = len(self.question.choices) - 1
            return

        # vi style
        if pressed in ("k", "h"):
            pressed = key.UP
        elif pressed in ("j", "l"):
            pressed = key.DOWN
        elif pressed == "q":
            pressed = key.CTRL_C

        # effect (rendering)
        super().process_input(pressed)

# ログ出力設定関数
def setLogger():
  script_name = __file__.split('/')[-1]
  log_dir_name = os.environ['HOME'] + '/.' + script_name.split('.')[0] + '/log'
  log_dir_base = log_dir_name + '/' if (os.path.exists(log_dir_name)) else './'

  dt = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
  logfile_name = log_dir_base + '{}_{}.log'.format(script_name, dt)

  logger = logging.getLogger(script_name)
  logger.setLevel(logging.INFO)

  fmt = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
  handler = logging.FileHandler(logfile_name)
  handler.setLevel(logging.INFO)
  handler.setFormatter(fmt)
  logger.addHandler(handler)

  fmt_stdout = logging.Formatter('%(message)s')
  handler_stdout= logging.StreamHandler()
  handler_stdout.setLevel(logging.INFO)
  handler_stdout.setFormatter(fmt_stdout)
  logger.addHandler(handler_stdout)

  return logger, logfile_name

def selected_answer(choices, message):
  questions = [
      inquirer.List(
          "answer",
          message=message,
          choices=choices,
          carousel=True,
      )
  ]
  answer = inquirer.prompt(questions, render=ExtendedConsoleRender(theme=themes.GreenPassion()))
  return json.loads(json.dumps(answer))['answer']


# クラスター名のチェック
def checkCluster(cluster_name):
  session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
  ecs = session.client('ecs')

  cluster_list = []
  for clusterArn in ecs.list_clusters()['clusterArns']:
    cluster = clusterArn.split('/')[len(clusterArn.split('/')) - 1]
    cluster_list.append(cluster)

  if cluster_name in cluster_list:
    return True
  else :
    return False

# クラスター名の設定
def setCluster(logger):
  session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
  ecs = session.client('ecs')

  cluster_list = []
  for clusterArn in ecs.list_clusters()['clusterArns']:
    cluster = clusterArn.split('/')[len(clusterArn.split('/')) - 1]
    cluster_list.append(cluster)

  cluster_name = selected_answer(cluster_list, "接続先が存在するクラスター名を選択してください")

  if checkCluster(cluster_name):
    logger.info('クラスター名: {}\n'.format(cluster_name))
    return cluster_name
  else :
    raise Exception('正しいクラスター名を選択してください。')

# サービス名のチェック
def checkService(cluster_name, service_name):
  session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
  ecs = session.client('ecs')

  service_list = []
  for serviceArn in ecs.list_services(
    cluster = cluster_name,
    maxResults = 100,
    launchType = 'FARGATE'
  )['serviceArns']:
    service = serviceArn.split('/')[len(serviceArn.split('/')) - 1]
    service_list.append(service)

  if service_name in service_list:
    return True
  else :
    return False

# サービス名の設定
def setService(logger, cluster_name):
  session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
  ecs = session.client('ecs')

  service_list = []
  for serviceArn in ecs.list_services(
    cluster = cluster_name,
    maxResults = 100,
    launchType = 'FARGATE'
  )['serviceArns']:
    service = serviceArn.split('/')[len(serviceArn.split('/')) - 1]
    service_list.append(service)

  service_name = selected_answer(service_list, "接続先が存在するサービス名を選択してください")
  if checkService(cluster_name, service_name):
    logger.info('サービス名: {}\n'.format(service_name))
    return service_name
  else :
    raise Exception('正しいサービス名を選択してください。')

# タスク名のチェック
def checkTask(cluster_name, service_name, task_name):
  session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
  ecs = session.client('ecs')

  task_list = []
  for taskArn in ecs.list_tasks(
    cluster = cluster_name,
    serviceName = service_name,
    desiredStatus = 'RUNNING',
    maxResults = 100,
    launchType = 'FARGATE'
  )['taskArns']:
    task = taskArn.split('/')[len(taskArn.split('/')) - 1]
    task_list.append(task)

  if task_name in task_list:
    return True
  else :
    return False

# タスク名の設定
def setTask(logger, cluster_name, service_name):
  session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
  ecs = session.client('ecs')

  task_list = []
  for taskArn in ecs.list_tasks(
    cluster = cluster_name,
    serviceName = service_name,
    desiredStatus = 'RUNNING',
    maxResults = 100,
    launchType = 'FARGATE'
  )['taskArns']:
    task = taskArn.split('/')[len(taskArn.split('/')) - 1]
    task_list.append(task)
  task_name = selected_answer(task_list, "接続先が存在するタスク名を選択してください")

  if checkTask(cluster_name, service_name, task_name):
    logger.info('タスク名: {}\n'.format(task_name))
    return task_name
  else :
    raise Exceptiont('正しいタスク名を選択してください。')

# コンテナ名のチェック
def checkContainer(cluster_name, task_name, container_name):
  session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
  ecs = session.client('ecs')

  task_detail_list = ecs.describe_tasks(
    cluster = cluster_name,
    tasks=[
      task_name
    ],
  )
  container_name_list = []
  for task in task_detail_list['tasks']:
    for container in task['overrides']['containerOverrides']:
      container_name_list.append(container['name'])

  if container_name in container_name_list:
    return True
  else :
    return False

# コンテナ名の設定
def setContainer(logger, cluster_name, task_name):
  session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
  ecs = session.client('ecs')

  container_list = []
  task_detail_list = ecs.describe_tasks(
    cluster = cluster_name,
    tasks=[
      task_name
    ],
  )
  for task in task_detail_list['tasks']:
    for container in task['overrides']['containerOverrides']:
      container_list.append(container['name'])

  container_name = selected_answer(container_list, "接続先のコンテナ名を選択してください")

  if checkContainer(cluster_name, task_name, container_name):
    logger.info('コンテナ名: {}\n'.format(container_name))
    return container_name
  else :
    raise Exception('正しいコンテナ名を選択してください。')

# FARGATEへ接続
def ecsExecute(logger, cluster_name, service_name, task_name, container_name, shell_cmd, logfile, force_connect):
  ## 接続先確認のメッセージを出力
  str  = '以下のFargateに接続します\n'
  str += '----------------------------------------\n'
  str += 'クラスター名: {}\n'.format(cluster_name)
  str += 'サービス名: {}\n'.format(service_name)
  str += 'タスク名: {}\n'.format(task_name)
  str += 'コンテナ名: {}\n'.format(container_name)
  str += '----------------------------------------\n'
  logger.info(str)
  if force_connect == False:
    is_exec= selected_answer(['yes', 'no'], "こちらに接続してよろしいですか")

  if force_connect == True or is_exec.startswith('y'):
    #session = boto3.session.Session(profile_name = os.environ['AWS_PROFILE'])
    #ecs = session.client('ecs')
    #ecs.execute_command(
    #  cluster = cluster_name,
    #  container = container_name,
    #  command = '/bin/bash',
    #  interactive = True,
    #  task = task_name
    #)
    #/bin/bashの場合セッションが切れてしまうためsubprocessを利用する方式に変更
    logger.info('Fargateにログインします')
    cmd  = '/usr/local/bin/aws ecs execute-command '
    cmd += '--cluster {} '.format(cluster_name)
    cmd += '--task {} '.format(task_name)
    cmd += '--container {} '.format(container_name)
    cmd += '--interactive --command {} | tee {}'.format(shell_cmd, logfile)

    ## Ctrl+C(SIGINTシグナル)を無視
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    ## subprocess実行
    out = subprocess.run(cmd, text=True, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, shell=True)
    logger.info(out)
    logger.info('Fargateからログアウトしました')
  return

def view_help():
  message = """
connect_to_fargate.py

Usage:
1. AWS_PROFILE を設定
  e.g.) export AWS_PROFILE=mpfront
2. sso login を行う
  aws sso login
3. コマンド実行
  connect_to_fargate.py [arguments]

Arguments:
   --help|-h                    help表示
   --cluster=<cluster_name>     クラスター名指定
   --service=<service_name>     サービス名指定
   --task=<task_name>           タスク名指定
   --container=<container_name> コンテナ名指定
   --cmd=<command>              コンテナで実行するコマンド（指定ない場合は、/bin/bash）
   --force                      接続確認なしでログインを行う
""".strip()

  print(message)

# 主処理
def main():
  try:
    logger, logfile = setLogger()

    ## 初期値の定義
    cluster_name, service_name, task_name, container_name = '', '', '', ''
    shell_cmd       = '/bin/bash'

    force_connect = False
    ## 引数の格納
    for a in sys.argv:
      if a.startswith('--cluster='):
        cluster_name = a.replace('--cluster=', '').strip('\'" []')
      elif a.startswith('--service='):
        service_name = a.replace('--service=', '').strip('\'" []')
      elif a.startswith('--task='):
        task_name = a.replace('--task=', '').strip('\'" []')
      elif a.startswith('--container='):
        container_name = a.replace('--container=', '').strip('\'" []')
      elif a.startswith('--cmd='):
        shell_cmd = a.replace('--cmd=', '').strip('\'" []')
      elif a.startswith('--force'):
        force_connect = True
      if a.startswith('--help') or a.startswith('-h'):
        view_help()
        return
    logger.info('処理を開始します')

    ## 引数で指定がない場合に設定する関数を実行する
    if cluster_name == '':
      cluster_name    = setCluster(logger)

    if service_name == '':
      if checkCluster(cluster_name):
        service_name    = setService(logger, cluster_name)
      else :
        raise Exception('正しいクラスター名を指定してください。')

    if task_name == '':
      if checkCluster(cluster_name) and \
         checkService(cluster_name, service_name):
        task_name       = setTask(logger, cluster_name, service_name)
      else :
        raise Exception('正しいクラスター名またはサービス名を指定してください。')

    if container_name == '':
      if checkCluster(cluster_name) and \
         checkService(cluster_name, service_name) and \
         checkTask(cluster_name, service_name, task_name):
        container_name  = setContainer(logger, cluster_name, task_name)
      else :
        raise Exception('正しいクラスター名またはサービス名またはタスク名を指定してください。')

    ## cluster_name, service_name, task_name, container_nameの実在確認（最終）
    if not checkCluster(cluster_name):
      raise Exception('正しいクラスター名を指定してください。')
    if not checkService(cluster_name, service_name):
      raise Exception('正しいサービス名を指定してください。')
    if not checkTask(cluster_name, service_name, task_name):
      raise Exception('正しいタスク名を指定してください。')
    if not checkContainer(cluster_name, task_name, container_name):
      raise Exception('正しいコンテナ名を指定してください。')

    ## Fargate接続関数を実行する
    ecsExecute(logger, cluster_name, service_name, task_name, container_name, shell_cmd, logfile, force_connect)
  except Exception as e:
    logger.error("処理を終了します\nエラー詳細: {}\n{}".format(e, traceback.format_exc()))
  return

# 実行処理
if __name__ == "__main__":
  main()

