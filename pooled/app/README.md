# Pooled Agent Service

Multi-tenant AI Agent Service - Pooled Architecture

## 概要

このアプリケーションは、マルチテナント環境でAIエージェントサービスを提供するためのpooled（プール型）アーキテクチャを実装しています。FastAPIとuvを使用してモダンで高性能なPython APIサービスを構築しています。

## 特徴

- 🚀 **高性能**: uvパッケージマネージャーとFastAPIによる高速な開発・実行
- 🏗️ **SOLID原則**: 保守性と拡張性を重視した設計
- 🔍 **包括的テスト**: 単体テスト・統合テストを含む
- 🐳 **Docker対応**: コンテナ化による一貫した実行環境
- 📊 **ヘルスチェック**: Kubernetes対応のヘルスチェックエンドポイント
- 📝 **自動ドキュメント**: OpenAPI/Swagger UI による API ドキュメント
- ☁️ **Azure Blob Storage**: Azure Blob Storageからのオブジェクト読み取り機能

## アーキテクチャ

```
src/
├── core/           # アプリケーションコア
│   ├── app.py     # アプリケーションファクトリー
│   └── config.py  # 設定管理
├── routers/        # HTTPルーティング
│   ├── health.py  # ヘルスチェックエンドポイント
│   ├── blob_storage.py # Blob Storageエンドポイント
│   └── root.py    # ルートエンドポイント
├── services/       # ビジネスロジック
│   ├── health_service.py
│   └── blob_storage_service.py
└── middleware/     # ミドルウェア
    ├── cors.py    # CORS設定
    └── logging.py # ログミドルウェア
```

## 必要な環境

- Python 3.12+
- uv (Pythonパッケージマネージャー)
- Docker (コンテナ実行用)

## インストール

### 1. uvのインストール

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Homebrew
brew install uv
```

### 2. 依存関係のインストール

```bash
# プロジェクトディレクトリに移動
cd pooled/app

# 依存関係をインストール
make install
```

### 3. 環境変数の設定

```bash
# 環境変数ファイルをコピー
cp .env.example .env

# 必要に応じて.envファイルを編集
# Azure Blob Storageの設定を追加
```

## 開発環境での実行

### ローカル開発

```bash
# 開発モード（ホットリロード有効）
make dev

# 本番モード
make run
```

アプリケーションは `http://localhost:8000` で利用可能になります。

### API ドキュメント

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker での実行

### 基本的な使い方

```bash
# 1. コンテナをビルド
make docker-build

# 2. バックグラウンドで実行
make docker-run

# 3. ログを確認
make docker-logs

# 4. ヘルスチェック確認
make docker-health
```

### インタラクティブ実行

```bash
# フォアグラウンドで実行（ログが直接表示される）
make docker-run-it
```

### コンテナ管理

```bash
# コンテナを停止・削除
make docker-stop

# コンテナ内でシェルを実行
make docker-shell

# 完全クリーンアップ（コンテナ・イメージ削除）
make docker-clean

# 再ビルド・再実行
make docker-restart
```

## ヘルスチェック

アプリケーションは以下のヘルスチェックエンドポイントを提供します：

| エンドポイント | 用途 | 説明 |
|---|---|---|
| `/health` | 基本ヘルスチェック | ロードバランサー・監視システム用 |
| `/health/ready` | レディネスチェック | Kubernetes用（依存関係の状態確認） |
| `/health/live` | ライブネスチェック | Kubernetes用（アプリケーション生存確認） |

### ヘルスチェックの確認

```bash
# 基本ヘルスチェック
curl http://localhost:8000/health

# レディネスチェック
curl http://localhost:8000/health/ready

# ライブネスチェック
curl http://localhost:8000/health/live
```

### レスポンス例

```json
{
  "status": "healthy",
  "timestamp": "2023-01-01T00:00:00Z",
  "service": "pooled-agent-service",
  "version": "0.1.0"
}
```

## テスト

### テスト環境のセットアップ

```bash
# テスト依存関係をインストール
make install-test
```

### テストの実行

```bash
# すべてのテスト実行
make test

# 単体テストのみ
make test-unit

# 統合テストのみ
make test-integration

# カバレッジ付きテスト
make test-cov

# 特定のテストファイル
make test-file FILE=tests/unit/test_health_service.py

# 詳細出力
make test-verbose
```

### テスト構成

- **単体テスト**: `tests/unit/` - 各コンポーネントの個別テスト
- **統合テスト**: `tests/integration/` - エンドツーエンドテスト
- **カバレッジ**: 80%以上のコードカバレッジを要求

## 利用可能なコマンド

### 開発用

| コマンド | 説明 |
|---|---|
| `make install` | 依存関係をインストール |
| `make dev` | 開発モードで実行（ホットリロード） |
| `make run` | 本番モードで実行 |

### Docker用

| コマンド | 説明 |
|---|---|
| `make docker-build` | Dockerイメージをビルド |
| `make docker-run` | コンテナをバックグラウンドで実行 |
| `make docker-run-it` | コンテナをインタラクティブ実行 |
| `make docker-stop` | コンテナを停止・削除 |
| `make docker-logs` | コンテナログを表示 |
| `make docker-shell` | コンテナ内でシェル実行 |
| `make docker-health` | ヘルスチェック状態を確認 |
| `make docker-clean` | コンテナとイメージを完全削除 |
| `make docker-restart` | 再ビルド・再実行 |

### テスト用

| コマンド | 説明 |
|---|---|
| `make test` | すべてのテスト実行 |
| `make test-unit` | 単体テストのみ |
| `make test-integration` | 統合テストのみ |
| `make test-cov` | カバレッジ付きテスト |
| `make test-verbose` | 詳細出力でテスト |
| `make clean` | テスト成果物をクリーンアップ |

## トラブルシューティング

### コンテナが起動しない場合

```bash
# コンテナの状態確認
docker ps -a

# ログの確認
make docker-logs

# ヘルスチェック状態
make docker-health
```

### よくあるエラーと解決方法

#### 1. `PydanticImportError: BaseSettings has been moved to the pydantic-settings package`

**症状**: コンテナが起動時にPydanticのインポートエラーで終了する

**原因**: Pydantic v2で`BaseSettings`が`pydantic-settings`パッケージに移動された

**解決方法**:
```python
# 修正前
from pydantic import BaseSettings

# 修正後
from pydantic_settings import BaseSettings
```

#### 2. モジュールインポートエラー

**症状**: `ModuleNotFoundError`が発生する

**解決方法**:
```bash
# 依存関係を再同期
uv sync

# コンテナを再ビルド
make docker-restart
```

### ポートが使用中の場合

```bash
# ポート8000を使用しているプロセスを確認
lsof -i :8000

# 他のポートで実行
docker run -it --rm -p 8080:8000 pooled-app
```

### テストが失敗する場合

```bash
# 詳細な出力でテスト実行
make test-verbose

# 特定のテストのみ実行
make test-file FILE=tests/unit/test_health_service.py

# テスト環境をクリーンアップ
make clean
```

### Docker関連の問題

#### コンテナのヘルスチェック確認
```bash
# Dockerのヘルスチェック状態
make docker-health

# 手動でヘルスチェックを実行
curl http://localhost:8000/health
```

#### ログの確認方法
```bash
# リアルタイムでログを監視
make docker-logs

# 最新のログのみ表示
docker logs --tail 50 pooled-app
```

## 貢献

1. フォークしてください
2. フィーチャーブランチを作成してください (`git checkout -b feature/amazing-feature`)
3. 変更をコミットしてください (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュしてください (`git push origin feature/amazing-feature`)
5. プルリクエストを作成してください

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## Azure Blob Storage

アプリケーションはAzure Blob Storageからオブジェクトを読み取る機能を提供します。

### エンドポイント

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/blobs/{blob_name}` | GET | Blobコンテンツを取得 |
| `/blobs/{blob_name}/stream` | GET | Blobコンテンツをストリーミング取得 |
| `/blobs/{blob_name}/metadata` | GET | Blobメタデータを取得 |
| `/blobs/{blob_name}` | HEAD | Blobの存在確認 |

### パラメータ

- **blob_name**: 取得するBlobの名前
- **container**: コンテナ名（オプション、デフォルトは設定値）
- **download**: ダウンロードとして強制する（`/blobs/{blob_name}`のみ）

### 使用例

```bash
# Blobコンテンツを取得
curl http://localhost:8000/blobs/document.pdf

# 特定のコンテナからBlobを取得
curl http://localhost:8000/blobs/document.pdf?container=my-container

# ダウンロードとして強制
curl http://localhost:8000/blobs/document.pdf?download=true

# Blobメタデータを取得
curl http://localhost:8000/blobs/document.pdf/metadata

# Blobの存在確認
curl -I http://localhost:8000/blobs/document.pdf
```

### 認証設定

Azure Blob Storageへの接続には以下の方法があります：

#### 1. 接続文字列（開発環境推奨）
```bash
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=youraccount;AccountKey=yourkey;EndpointSuffix=core.windows.net
```

#### 2. アカウント名とキー
```bash
AZURE_STORAGE_ACCOUNT_NAME=youraccount
AZURE_STORAGE_ACCOUNT_KEY=yourkey
```

#### 3. マネージドID（本番環境推奨）
```bash
AZURE_STORAGE_ACCOUNT_NAME=youraccount
# DefaultAzureCredentialを使用
```
