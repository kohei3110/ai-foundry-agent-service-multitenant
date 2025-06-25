# Pooled Agent Service 開発者ガイド

## 目次
1. [開発環境のセットアップ](#開発環境のセットアップ)
2. [プロジェクト構造](#プロジェクト構造)
3. [ローカル開発](#ローカル開発)
4. [テスト](#テスト)
5. [デバッグ](#デバッグ)
6. [コーディング規約](#コーディング規約)
7. [コントリビューション](#コントリビューション)

## 開発環境のセットアップ

### 前提条件
- Python 3.12 以上
- Git
- Docker (コンテナ実行用)
- Azure CLI (Azure リソースアクセス用)

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd ai-foundry-agent-service-multitenant/pooled/app
```

### 2. uv パッケージマネージャーのインストール
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. 仮想環境の作成と依存関係のインストール
```bash
# 開発用依存関係も含めてインストール
uv sync --extra test

# または本番依存関係のみ
uv sync
```

### 4. 環境変数の設定
`.env` ファイルを作成し、必要な環境変数を設定：

```bash
# .env ファイルの例
APP_NAME="Pooled Agent Service"
DEBUG=true
LOG_LEVEL=DEBUG

# Azure Storage 設定
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account
AZURE_STORAGE_ACCOUNT_KEY=your_account_key
# または
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_STORAGE_CONTAINER_NAME=documents
```

## プロジェクト構造

```
pooled/app/
├── src/                    # アプリケーションソースコード
│   ├── core/              # アプリケーションコア
│   │   ├── __init__.py
│   │   ├── app.py         # FastAPIアプリケーションファクトリー
│   │   └── config.py      # 設定管理
│   ├── routers/           # HTTPルーティング
│   │   ├── __init__.py
│   │   ├── root.py        # ルートエンドポイント
│   │   ├── health.py      # ヘルスチェック
│   │   └── blob_storage.py # Blob Storage API
│   ├── services/          # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── blob_storage_service.py
│   │   └── health_service.py
│   └── middleware/        # ミドルウェア
│       ├── __init__.py
│       ├── cors.py        # CORS設定
│       └── logging.py     # ログミドルウェア
├── tests/                 # テストコード
│   ├── unit/             # 単体テスト
│   ├── integration/      # 統合テスト
│   └── conftest.py       # pytest設定
├── main.py               # アプリケーションエントリーポイント
├── pyproject.toml        # プロジェクト設定
├── uv.lock              # 依存関係ロック
├── Dockerfile           # Docker設定
└── README.md            # プロジェクト説明
```

### アーキテクチャの特徴

#### 1. レイヤード アーキテクチャ
- **Router Layer**: HTTP リクエストの処理とルーティング
- **Service Layer**: ビジネスロジックの実装
- **Core Layer**: アプリケーション設定とファクトリー

#### 2. SOLID 原則の適用
- **Single Responsibility**: 各クラスは単一の責任を持つ
- **Open/Closed**: 拡張に開放、修正に閉鎖
- **Liskov Substitution**: 派生クラスは基底クラスと置換可能
- **Interface Segregation**: インターフェースの分離
- **Dependency Inversion**: 依存性の逆転

#### 3. 依存性注入
FastAPIの`Depends`を使用して依存性注入を実現：

```python
@router.get("/{blob_name}")
async def get_blob_content(
    blob_name: str,
    blob_service: BlobStorageInterface = Depends(get_blob_storage_service)
):
    # ...
```

## ローカル開発

### 1. 開発サーバーの起動
```bash
# uvを使用して起動
uv run python main.py

# または直接実行
python main.py

# リロード機能付きで起動
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. API ドキュメントの確認
開発サーバー起動後、以下のURLでAPI ドキュメントにアクセスできます：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### 3. ログの確認
アプリケーションは構造化ログを出力します：

```
2024-06-25 10:30:00,123 - src.routers.blob_storage - INFO - Request to get blob: document.pdf from container: documents
2024-06-25 10:30:00,150 - src.middleware.logging - INFO - Request completed - GET /blobs/document.pdf - 200
```

各リクエストには一意の correlation ID が付与され、レスポンスヘッダーで確認できます。

## テスト

### テスト構造
```
tests/
├── unit/              # 単体テスト
│   ├── test_services/
│   ├── test_routers/
│   └── test_core/
├── integration/       # 統合テスト
│   ├── test_api/
│   └── test_blob_storage/
└── conftest.py       # 共通テスト設定
```

### 1. テストの実行

#### 全テスト実行
```bash
uv run pytest
```

#### 単体テストのみ実行
```bash
uv run pytest tests/unit/
```

#### カバレッジ付きでテスト実行
```bash
uv run pytest --cov=src --cov-report=html
```

### 2. テストの書き方

#### 単体テストの例
```python
import pytest
from unittest.mock import AsyncMock
from src.services.blob_storage_service import AzureBlobStorageService

@pytest.mark.asyncio
async def test_get_blob_success():
    # Arrange
    service = AzureBlobStorageService("account", "key", "", "container")
    service._blob_service_client = AsyncMock()
    
    # Act
    result = await service.get_blob("test.txt")
    
    # Assert
    assert result is not None
```

#### 統合テストの例
```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

### 3. モッキング
Azure サービスのモッキングには `pytest-mock` を使用：

```python
def test_blob_service_with_mock(mocker):
    mock_client = mocker.patch('azure.storage.blob.BlobServiceClient')
    # テストロジック
```

## デバッグ

### 1. IDE設定

#### VS Code
`.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "program": "main.py",
            "console": "integratedTerminal",
            "env": {
                "DEBUG": "true",
                "LOG_LEVEL": "DEBUG"
            }
        }
    ]
}
```

### 2. ログレベルの調整
開発時は詳細なログを確認するため、DEBUG レベルに設定：

```bash
export LOG_LEVEL=DEBUG
```

### 3. プロファイリング
パフォーマンス問題のデバッグ：

```python
import cProfile
import pstats

# プロファイリング実行
cProfile.run('your_function()', 'profile_output')
stats = pstats.Stats('profile_output')
stats.sort_stats('cumulative').print_stats(10)
```

## コーディング規約

### 1. PEP 8 準拠
```bash
# フォーマッタの実行
uv run black src/
uv run isort src/

# リンターの実行
uv run flake8 src/
uv run mypy src/
```

### 2. 型ヒント
すべての関数・メソッドに型ヒントを追加：

```python
from typing import Optional, Dict, Any

async def get_blob_metadata(
    self, 
    blob_name: str, 
    container_name: Optional[str] = None
) -> Dict[str, Any]:
    # 実装
```

### 3. docstring 規約
Google スタイルのdocstringを使用：

```python
def example_function(param1: str, param2: int) -> bool:
    """Example function with Google-style docstring.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        The return value. True for success, False otherwise.

    Raises:
        ValueError: If param1 is empty.
    """
```

### 4. ログメッセージ
構造化ログを使用し、機密情報の漏洩を防ぐ：

```python
logger.info(f"Processing blob: {blob_name}", extra={
    "blob_name": blob_name,
    "container": container_name,
    "user_id": user_id  # ただし、機密情報は除く
})
```

### 5. エラーハンドリング
適切な例外処理と再発生：

```python
try:
    result = await external_service.call()
except ExternalServiceError as e:
    logger.error(f"External service error: {e}")
    raise CustomServiceError(f"Failed to call external service: {e}")
```

## コントリビューション

### 1. 開発フロー
1. Issue の作成または確認
2. フィーチャーブランチの作成
3. 開発とテストの実施
4. プルリクエストの作成
5. コードレビュー
6. マージ

### 2. ブランチ規約
```bash
# フィーチャーブランチ
feature/issue-123-add-upload-api

# バグ修正ブランチ
bugfix/issue-456-fix-auth-error

# ホットフィックス
hotfix/critical-security-patch
```

### 3. コミットメッセージ
```bash
# 形式
type(scope): subject

# 例
feat(blob): add file upload functionality
fix(health): correct readiness check logic
docs(api): update API documentation
test(integration): add blob storage integration tests
```

### 4. プルリクエスト
- [ ] テストが通過している
- [ ] ドキュメントが更新されている
- [ ] コードレビューが完了している
- [ ] 競合が解決されている

### 5. コードレビューのポイント
- SOLID 原則の遵守
- セキュリティの考慮
- パフォーマンスの影響
- テストカバレッジ
- ドキュメントの整合性

## トラブルシューティング

### よくある問題

#### 1. Azure Storage 接続エラー
```bash
# 接続文字列の確認
az storage account show-connection-string --name <account-name>

# 認証の確認
az login
```

#### 2. 依存関係のエラー
```bash
# 依存関係の再インストール
uv sync --reinstall
```

#### 3. ポート競合
```bash
# 使用中のポートの確認
lsof -i :8000

# 別のポートで起動
uv run uvicorn main:app --port 8001
```

### デバッグのヒント
1. ログレベルを DEBUG に設定
2. Correlation ID でリクエストを追跡
3. Azure Portal でストレージアクセスログを確認
4. ネットワーク接続の確認

---

**最終更新**: 2024年6月25日  
**バージョン**: 1.0
