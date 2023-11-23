# Fargate接続ツールの説明

## 事前準備
- クライアント側でECS Execを利用可能にしておく
- 参考情報
  - https://docs.aws.amazon.com/ja_jp/AmazonECS/latest/userguide/ecs-exec.html
  - https://docs.aws.amazon.com/ja_jp/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html


## 利用方法
```
# Profileを設定して、sso login する
export AWS_PROFILE=profile_name; aws sso login
(url をブラウザで参照し、 codeを入力する)

# 必要モジュールのインストール
pip install boto3
pip install inquirer

# Session Manager プラグインインストール(下記URLはMacOSでのインストール方法)
https://docs.aws.amazon.com/ja_jp/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html#install-plugin-macos

# リンク作成
sudo ln -s $(pwd)/connect_to_fargate.py /usr/local/bin

# ログディレクトリ作成(任意)
mkdir -p ~/.connect_to_fargate/log

# スクリプト実行する
connect_to_fargate.py

※connect_to_fargate.py_(日時).logにログが出力されます。

※引数に以下を利用できるように追加しました。
--cluster=クラスター名（指定ない場合は、対話型の選択画面に遷移）
--service=サービス名（指定ない場合は、対話型の選択画面に遷移）
--task=タスク名（指定ない場合は、対話型の選択画面に遷移）
--container=コンテナ名（指定ない場合は、対話型の選択画面に遷移）
--cmd=コンテナで実行するコマンド（指定ない場合は、/bin/bash）

※Ctrl + Cの挙動は変更しました（接続処理直前にSIGINTをSIG_IGNに変換する処理を追加）
```

### 実行結果（例１ 引数なし）
```
$ connect_to_fargate.py
処理を開始します
[?] 接続先が存在するクラスター名を選択してください: default
 ❯ default
   cluster_a
   cluster_b

クラスター名: default

[?] 接続先が存在するサービス名を選択してください: ticketpay-wordpress-development
 ❯ service_a
   service_b

サービス名: service_a

[?] 接続先が存在するタスク名を選択してください: 779933414f454c76960d15b37ab15f26
 ❯ 779933414f454c76960d15b37ab15f26

タスク名: 779933414f454c76960d15b37ab15f26

[?] 接続先のコンテナ名を選択してください: app
 ❯ app
   web

コンテナ名: app

以下のFargateに接続します
----------------------------------------
クラスター名: default
サービス名: service_a
タスク名: 779933414f454c76960d15b37ab15f26
コンテナ名: app
----------------------------------------

[?] こちらに接続してよろしいですか: yes
 ❯ yes
   no

Fargateにログインします

The Session Manager plugin was installed successfully. Use the AWS CLI to start a session.


Starting session with SessionId: ecs-execute-command-08107c57e1eb5fee9
root@ip-172-30-2-204:/#
↑コンテナにログインしている
exit


Exiting session with sessionId: ecs-execute-command-08107c57e1eb5fee9.

CompletedProcess(args='/usr/local/bin/aws ecs execute-command --cluster fumizawa-test-cluster --task 87b5a48c8b99450d9dea5443c863ee5d --container nginx --interactive --command /bin/bash | tee ./connect_to_fargate.py_20220629090944872720.log', returncode=0)
Fargateからログアウトしました
```

### 実行結果（例２ 一部引数あり）
```
$ connect_to_fargate.py --cluster=default --container=web
処理を開始します
[?] 接続先が存在するサービス名を選択してください: ticketpay-wordpress-development
 ❯ service_a
   service_b

サービス名: service_a

[?] 接続先が存在するタスク名を選択してください: 779933414f454c76960d15b37ab15f26
 ❯ 779933414f454c76960d15b37ab15f26

タスク名: 779933414f454c76960d15b37ab15f26

以下のFargateに接続します
----------------------------------------
クラスター名: default
サービス名: service_a
タスク名: ae95d0c222424643be7ddd8e288b1229
コンテナ名: web
----------------------------------------

[?] こちらに接続してよろしいですか: yes
 ❯ yes
   no

Fargateにログインします
（略）
```

### 実行結果（例３ fargatessh利用）
```
$ fargatessh -p profile -c default -t app -f

処理を開始します
[?] 接続先が存在するサービス名を選択してください: ticketpay-wordpress-development
 ❯ service_a
   service_b

サービス名: service_a

[?] 接続先が存在するタスク名を選択してください: 779933414f454c76960d15b37ab15f26
 ❯ 779933414f454c76960d15b37ab15f26

タスク名: 779933414f454c76960d15b37ab15f26

以下のFargateに接続します
----------------------------------------
クラスター名: default
サービス名: service_a
タスク名: ae95d0c222424643be7ddd8e288b1229
コンテナ名: web
----------------------------------------

Fargateにログインします
（略）
```

## トラブルシューティング
'ServiceNotActiveException'が発生した場合
以下を実行して新しいタスクに入れ替える
```
aws ecs update-service \
--cluster (クラスター名) \ 
--service (サービス名) \
--enable-execute-command
'TargetNotConnectedException'が発生した場合
正しいセキュリティグループにしているか、ネットワーク経路が確保されているかを確認する
```

### 汎用的な調査方法
https://github.com/aws-containers/amazon-ecs-exec-checker
check-ecs-execを実行する
```
[実行例]
$ check-ecs-exec.sh (クラスター名) (タスク名)
※/usr/local/binに配置しているため

[実行結果]
-------------------------------------------------------------
Prerequisites for check-ecs-exec.sh v0.7
-------------------------------------------------------------
  jq      | OK (/usr/bin/jq)
  AWS CLI | OK (/usr/local/bin/aws)

-------------------------------------------------------------
Prerequisites for the AWS CLI to use ECS Exec
-------------------------------------------------------------
  AWS CLI Version        | OK (aws-cli/2.6.3 Python/3.9.11 Linux/5.10.118-111.515.amzn2.x86_64 exe/x86_64.amzn.2 prompt/off)
  Session Manager Plugin | OK (1.2.339.0)

-------------------------------------------------------------
Checks on ECS task and other resources
-------------------------------------------------------------
Region : ap-northeast-1
Cluster: (クラスター名)
Task   : (タスク名)
-------------------------------------------------------------
  Cluster Configuration  | Audit Logging Not Configured
  Can I ExecuteCommand?  | arn:aws:iam::172972874842:role/aws-reserved/sso.amazonaws.com/ap-northeast-1/AWSReservedSSO_Administrators@FrontSystem_10607a14223798a0
     ecs:ExecuteCommand: allowed
     ssm:StartSession denied?: allowed
  Task Status            | RUNNING
  Launch Type            | Fargate
  Platform Version       | 1.4.0
  Exec Enabled for Task  | NO　　　←今回の実行例の場合はこれが原因
  Container-Level Checks |
    ----------
      Managed Agent Status - SKIPPED
    ----------
    ----------
      Init Process Enabled ((タスク名):(タスクのバージョン))
    ----------
         1. Disabled - "web"
         2. Disabled - "app"
    ----------
      Read-Only Root Filesystem ((タスク名):(タスクのバージョン))
    ----------
         1. Disabled - "web"
         2. Disabled - "app"
  Task Role Permissions  | arn:aws:iam::172972874842:role/ecsTaskRole
     ssmmessages:CreateControlChannel: allowed
     ssmmessages:CreateDataChannel: allowed
     ssmmessages:OpenControlChannel: allowed
     ssmmessages:OpenDataChannel: allowed
  VPC Endpoints          |
    Found existing endpoints for vpc-01cd9e8961a6cca07:
      - com.amazonaws.ap-northeast-1.s3
      - com.amazonaws.ap-northeast-1.kms
      - com.amazonaws.ap-northeast-1.ec2messages
      - com.amazonaws.ap-northeast-1.ssm
      - com.amazonaws.ap-northeast-1.ssmmessages
      - com.amazonaws.ap-northeast-1.secretsmanager
  Environment Variables  | (kaihipay-wordpress-development:37)
       1. container "web"
       - AWS_ACCESS_KEY: not defined
       - AWS_ACCESS_KEY_ID: not defined
       - AWS_SECRET_ACCESS_KEY: not defined
       2. container "app"
       - AWS_ACCESS_KEY: not defined
       - AWS_ACCESS_KEY_ID: not defined
       - AWS_SECRET_ACCESS_KEY: not defined
 ```
