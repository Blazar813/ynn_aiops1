# Hermes Agentic AIOps 実行手順書

## 1. このシステムについて

このプロジェクトは、Hermes AgentをAIエージェントの実行基盤として利用するAgentic AIOpsのサンプル実装です。

監視アラートを入力すると、Hermes AgentがMCP（Model Context Protocol）経由でAIOpsツールを呼び出し、次の処理を行います。

1. インシデント情報を取得する
2. 対象サービスのログを検索する
3. サービスのヘルス状態を確認する
4. 障害原因と対応方針を判断する
5. 必要に応じて復旧操作を実行する
6. 実行結果と残存リスクを報告する

Hermes Agent本体の標準CLIと、Hermesが標準対応するMCPサーバー設定を使用します。独自のLLM推論ループや独自JSON-RPC実装は使用していません。

## 2. ディレクトリ構成

```text
.
├── Start-AIOps.ps1                  # AIOps実行用PowerShellスクリプト
├── scripts/
│   └── Install-AIOps.ps1            # セットアップ用スクリプト
├── config/
│   └── hermes-aiops.yaml            # Hermes用MCP設定
├── src/
│   └── aiops_mcp_server.py          # AIOps MCPサーバー
├── tests/
│   └── test_aiops_mcp_server.py     # MCPサーバーのテスト
├── requirements.txt                 # Python依存パッケージ
├── artifacts/runs/                  # 実行時に生成される監査ログ
└── .hermes/                         # プロジェクト専用のHermes設定
```

## 3. 前提ソフトウェア

以下を用意してください。

- Windows 10またはWindows 11
- Windows PowerShell 5.1以上、またはPowerShell 7
- Python 3.11以上
- Hermes Agent
- Hermesで利用可能なモデルプロバイダー

Pythonの確認：

```powershell
python --version
```

`Python 3.11`以上が表示されない場合は、Pythonをインストールしてから次に進んでください。

## 4. Hermes Agentのインストール

PowerShellで、公式インストーラーを実行します。

```powershell
Set-ExecutionPolicy -Scope Process Bypass
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

インストール後、現在のPowerShellではPATHが更新されない場合があります。PowerShellをいったん閉じて、新しいPowerShellを開いてください。

インストール確認：

```powershell
Get-Command hermes
hermes --version
```

`hermes`が見つからない場合は、PowerShellを再起動してから再実行してください。

## 5. AIOpsプロジェクトのセットアップ

プロジェクトのルートディレクトリに移動します。

```powershell
Set-Location "C:\Users\ynakayama1.IXAS\ynn_aiops1"
```

セットアップスクリプトを実行します。

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\Install-AIOps.ps1
```

このスクリプトは、Hermes Agentが未インストールの場合の公式インストール、`.venv`というPython仮想環境の作成、`requirements.txt`に記載されたMCPライブラリのインストールを行います。

Hermesのインストールを行わず、Python環境だけセットアップする場合：

```powershell
.\scripts\Install-AIOps.ps1 -SkipHermes
```

## 6. Hermesのモデル設定

このプロジェクトでは、個人設定と分離するため、プロジェクト内の`.hermes`をHermesのホームディレクトリとして使用します。

まず、PowerShellで環境変数を設定します。

```powershell
$env:HERMES_HOME = (Join-Path (Get-Location) '.hermes')
```

通常の対話式セットアップを開始します。

```powershell
hermes setup
```

Nous Portalを利用する場合：

```powershell
hermes setup --portal
```

設定後、通常のチャットが動作することを確認します。

```powershell
hermes chat -q "Return only the word OK"
```

この確認が失敗する場合は、AIOpsを実行する前にHermesのモデル設定または認証を修正してください。

`$env:HERMES_HOME`はPowerShellを閉じると解除されます。実行のたびに、先に設定してください。

## 7. MCP設定とツール

`config\hermes-aiops.yaml`には、HermesがAIOps MCPサーバーを起動するための設定が記載されています。`Start-AIOps.ps1`が実行時にこの設定をプロジェクト専用のHermes設定へコピーします。

MCPサーバーには次のツールが登録されます。

| ツール | 目的 | 読み取り・変更 |
|---|---|---|
| `get_incident_context` | アラートと対応範囲の取得 | 読み取り |
| `search_logs` | サービスログの検索 | 読み取り |
| `get_service_health` | サービス状態の確認 | 読み取り |
| `execute_remediation` | 復旧操作の実行またはドライラン | 変更操作 |

## 8. AIOpsの実行

### 8.1 調査だけを行う場合

`-AutoRemediate`を付けずに実行します。

```powershell
.\Start-AIOps.ps1 `
  -ServiceName "payment-service" `
  -Alert "HTTP 504 Gateway Timeout"
```

このモードではログ調査とヘルスチェックを行います。復旧操作はドライランとして扱われ、外部システムの変更は行われません。

### 8.2 自動復旧を許可する場合

自動復旧を許可する場合は、`-AutoRemediate`を指定します。

```powershell
.\Start-AIOps.ps1 `
  -ServiceName "payment-service" `
  -Alert "HTTP 504 Gateway Timeout" `
  -AutoRemediate
```

現在のサンプル実装では、実際の外部システムは変更せず、ドライラン結果を返します。

実変更を有効にするには、`-AutoRemediate`に加えて、`AIOPS_ALLOW_MUTATIONS=true`と一致する承認トークンが必要です。

```powershell
$env:AIOPS_APPROVAL_TOKEN = "承認トークン"

.\Start-AIOps.ps1 `
  -ServiceName "payment-service" `
  -Alert "HTTP 504 Gateway Timeout" `
  -AutoRemediate `
  -ApprovalToken "承認トークン"
```

本番環境では、`src\aiops_mcp_server.py`のデモ用復旧処理を、実際の運用API、Kubernetes、クラウド、監視製品、デプロイ基盤などのAPI呼び出しへ置き換えてください。

### 8.3 使用モデルを指定する場合

Hermesで利用可能なモデルを明示できます。

```powershell
.\Start-AIOps.ps1 `
  -ServiceName "payment-service" `
  -Alert "HTTP 504 Gateway Timeout" `
  -Model "モデル名"
```

### 8.4 最大ターン数を指定する場合

Hermesがツールを呼び出せる最大反復回数は、既定で8回です。

```powershell
.\Start-AIOps.ps1 `
  -ServiceName "payment-service" `
  -Alert "HTTP 504 Gateway Timeout" `
  -MaxTurns 12
```

## 9. 実行結果の確認

実行すると、`artifacts\runs`にJSONL形式の監査ログが作成されます。

```powershell
Get-ChildItem .\artifacts\runs
```

最新ログを確認する例：

```powershell
$latest = Get-ChildItem .\artifacts\runs\*.jsonl |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
Get-Content $latest.FullName
```

ログには、主に次のイベントが含まれます。

- `system`: Hermesセッションの初期化情報
- `tool_use`: Hermesが呼び出したMCPツールと引数
- `text`: Hermesの分析・報告テキスト
- 終了情報: Hermesの実行結果やエラー

## 10. サンプルデータ

初期状態では、`src\aiops_mcp_server.py`に次のデモログが定義されています。

- `payment-service`の正常トランザクション
- データベース接続プール枯渇
- トランザクションテーブルのデッドロック

そのため、次の実行では`payment-service`が`degraded`と判定されます。

```powershell
.\Start-AIOps.ps1 `
  -ServiceName "payment-service" `
  -Alert "HTTP 504 Gateway Timeout"
```

## 11. テスト

pytestを追加インストールする場合：

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
```

テスト実行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Pythonファイルの構文確認：

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  .\src\aiops_mcp_server.py `
  .\tests\test_aiops_mcp_server.py
```

## 12. トラブルシューティング

### `hermes`が見つからない

Hermesインストール後にPowerShellを再起動してください。

```powershell
Get-Command hermes
```

### `.venv`が見つからない

プロジェクトルートでセットアップを実行してください。

```powershell
.\scripts\Install-AIOps.ps1 -SkipHermes
```

### Hermesの認証・モデルエラーが出る

まず、AIOpsを実行せずに通常のHermesチャットを確認します。

```powershell
$env:HERMES_HOME = (Join-Path (Get-Location) '.hermes')
hermes chat -q "Return only the word OK"
```

### MCPツールが見つからない

次を確認してください。

1. `.venv`が作成済みである
2. `mcp`パッケージがインストール済みである
3. `$env:HERMES_HOME`がプロジェクトの`.hermes`を指している
4. `config\hermes-aiops.yaml`が存在する
5. プロジェクトルートから`Start-AIOps.ps1`を実行している

```powershell
.\.venv\Scripts\python.exe -m pip show mcp
```

### 実行が途中で停止する

最新の実行ログを確認してください。

```powershell
Get-ChildItem .\artifacts\runs |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 |
  Get-Content
```

必要に応じて`-MaxTurns`を増やします。

### 復旧操作が`dry-run`になる

安全のための既定動作です。実変更には次の条件が必要です。

- `-AutoRemediate`を指定している
- `AIOPS_ALLOW_MUTATIONS=true`が設定されている
- `-ApprovalToken`が`AIOPS_APPROVAL_TOKEN`と一致している

## 13. 本番利用時の注意

このリポジトリのMCPサーバーはデモ用です。本番導入前に、少なくとも次を実装してください。

- 監視システムからの実アラート受信
- ログ基盤への読み取り専用接続
- サービスヘルスチェックAPIへの接続
- 復旧操作の対象・操作種別・環境の許可リスト
- 承認ワークフローと監査証跡
- 操作のタイムアウト、リトライ、冪等性
- 復旧後の検証とロールバック
- APIキーやトークンの安全な保管
- 本番・ステージング・開発環境の分離

LLMに復旧操作の権限を直接与えず、MCPサーバー側で必ず認可・対象制限・承認確認を実施してください。

## 14. 参考資料

- [Hermes Agent公式サイト](https://hermes-agent.nousresearch.com/)
- [Hermes Agent GitHub](https://github.com/nousresearch/hermes-agent)
- [Hermes MCPガイド](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [Hermes MCP設定リファレンス](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference)
- [Hermes CLIリファレンス](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)
