# Pooled Agent Service アプリケーション仕様書

## 1. 概要

### 1.1 プロジェクト概要
- **プロジェクト名**: Pooled Agent Service
- **バージョン**: 0.1.0
- **説明**: マルチテナント AI エージェントサービス - プール型アーキテクチャ
- **アーキテクチャパターン**: Pooled Architecture（共有リソース型）
- **実装言語**: Python 3.12+
- **フレームワーク**: FastAPI
- **パッケージマネージャー**: uv

### 1.2 目的
プール型アーキテクチャを使用して、複数のテナントが共有リソース上でAIエージェントサービスを利用できる、スケーラブルで効率的なマルチテナントアプリケーションを提供する。

### 1.3 主要機能
- Azure Blob Storage からのファイルアクセス機能（SAS認証）
- SASトークン生成機能
- ヘルスチェック機能（Kubernetes対応）
- CORS対応
- 構造化ログ機能
- 自動API ドキュメント生成（OpenAPI/Swagger）

## 2. アーキテクチャ設計

### 2.1 全体アーキテクチャ
```
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway / Load Balancer              │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Pooled Agent Service                       │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐      │
│  │   Router      │ │  Middleware   │ │   Service     │      │
│  │               │ │               │ │               │      │
│  │ • Root        │ │ • CORS        │ │ • Blob Storage│      │
│  │ • Health      │ │ • Logging     │ │ • Health      │      │
│  │ • Blob Storage│ │               │ │               │      │
│  └───────────────┘ └───────────────┘ └───────────────┘      │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Azure Blob Storage                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 レイヤードアーキテクチャ
```
src/
├── core/               # アプリケーションコア層
├── routers/            # プレゼンテーション層
├── services/           # ビジネスロジック層
└── middleware/         # インフラストラクチャ層
```

### 2.3 設計原則
- **SOLID原則**: 単一責任、開放閉鎖、リスコフ置換、インターフェース分離、依存性逆転
- **Dependency Injection**: 依存性注入によるテスタビリティの向上
- **Interface Segregation**: 抽象化によるモジュラリティ
- **Factory Pattern**: アプリケーションファクトリーによる設定管理

### 2.4 SASトークンアーキテクチャ

SAS（Shared Access Signature）トークンを使用した安全なBlob Storageアクセスを実装：

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Request                             │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   API Service                                │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐      │
│  │  SAS Token    │ │  Blob Service │ │     HTTP      │      │
│  │   Service     │ │               │ │    Client     │      │
│  │ • Token生成   │ │ • メタデータ  │ │ • SAS URL     │      │
│  │ • URL構築     │ │ • 存在確認    │ │   アクセス    │      │
│  └───────────────┘ └───────────────┘ └───────────────┘      │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│              Azure Blob Storage (Private)                    │
│  • SASトークンによる時間制限アクセス                        │
│  • 読み取り専用権限                                         │
└─────────────────────────────────────────────────────────────┘
```

**セキュリティ特徴:**
- プライベートBlob Storageへの安全なアクセス
- 時間制限付きアクセス（1-24時間）
- 読み取り専用権限
- HTTPSによる暗号化通信

## 3. API仕様

### 3.1 エンドポイント一覧

| Method | Path | 説明 | 認証 |
|--------|------|------|------|
| GET | / | ルートエンドポイント（サービス情報） | 不要 |
| GET | /health | 基本ヘルスチェック | 不要 |
| GET | /health/ready | Kubernetes readiness プローブ | 不要 |
| GET | /health/live | Kubernetes liveness プローブ | 不要 |
| GET | /blobs/{blob_name} | Blob コンテンツ取得（SAS認証） | 不要 |
| GET | /blobs/{blob_name}/stream | Blob ストリーミング取得（SAS認証） | 不要 |
| GET | /blobs/{blob_name}/metadata | Blob メタデータ取得（SAS認証） | 不要 |
| GET | /blobs/{blob_name}/sas | SASトークン生成 | 不要 |
| HEAD | /blobs/{blob_name} | Blob 存在確認（SAS認証） | 不要 |

### 3.2 API詳細仕様

#### 3.2.1 ルートエンドポイント
```http
GET /
```

**レスポンス例:**
```json
{
  "message": "Pooled Agent Service is running",
  "architecture": "pooled",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

#### 3.2.2 ヘルスチェックエンドポイント

##### 基本ヘルスチェック
```http
GET /health
```

**レスポンス例:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "pooled-agent-service",
  "version": "0.1.0"
}
```

##### Readiness チェック
```http
GET /health/ready
```

**レスポンス例:**
```json
{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": "ok",
    "external_apis": "ok"
  }
}
```

##### Liveness チェック
```http
GET /health/live
```

**レスポンス例:**
```json
{
  "status": "alive",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 3600.25
}
```

#### 3.2.3 Blob Storage エンドポイント

##### Blob コンテンツ取得
```http
GET /blobs/{blob_name}?container={container_name}&download={boolean}
```

**パラメータ:**
- `blob_name` (path): 取得するBlobの名前
- `container` (query, optional): コンテナ名（省略時はデフォルトコンテナ）
- `download` (query, optional): ダウンロード強制フラグ

**レスポンスヘッダー:**
- `Content-Length`: ファイルサイズ
- `Content-Type`: MIMEタイプ
- `ETag`: ファイルのETag
- `Last-Modified`: 最終更新日時
- `Content-Disposition`: ダウンロード時の添付ファイル指定

##### Blob ストリーミング取得
```http
GET /blobs/{blob_name}/stream?container={container_name}
```

**特徴:**
- 大容量ファイルのストリーミング配信
- メモリ効率的な転送

##### Blob メタデータ取得
```http
GET /blobs/{blob_name}/metadata?container={container_name}
```

**レスポンス例:**
```json
{
  "name": "document.pdf",
  "container": "documents",
  "size": 1024000,
  "content_type": "application/pdf",
  "last_modified": "2024-01-15T10:30:00Z",
  "etag": "\"0x8D9A1B2C3D4E5F6\"",
  "metadata": {},
  "creation_time": "2024-01-15T09:00:00Z"
}
```

##### SASトークン生成
```http
GET /blobs/{blob_name}/sas?container={container_name}&expires_in_hours={hours}
```

**パラメータ:**
- `blob_name` (path): SASトークンを生成するBlobの名前
- `container` (query, optional): コンテナ名（省略時はデフォルトコンテナ）
- `expires_in_hours` (query, optional): SASトークンの有効期限（時間、デフォルト: 1、最大: 24）

**レスポンス例:**
```json
{
  "blob_name": "document.pdf",
  "container": "documents",
  "sas_token": "sp=r&st=2024-06-25T10:30:00Z&se=2024-06-25T11:30:00Z&spr=https&sv=2022-11-02&sr=b&sig=abc123...",
  "blob_url": "https://mystorageaccount.blob.core.windows.net/documents/document.pdf?sp=r&st=2024-06-25T10:30:00Z&se=2024-06-25T11:30:00Z&spr=https&sv=2022-11-02&sr=b&sig=abc123...",
  "expires_in_hours": 1
}
```

##### Blob 存在確認
```http
HEAD /blobs/{blob_name}?container={container_name}
```

**レスポンス:**
- 200: Blob が存在
- 404: Blob が存在しない

## 4. 設定仕様

### 4.1 環境変数

| 変数名 | 型 | デフォルト値 | 説明 |
|--------|----|-----------|----|
| `APP_NAME` | string | "Pooled Agent Service" | アプリケーション名 |
| `APP_VERSION` | string | "0.1.0" | アプリケーションバージョン |
| `HOST` | string | "0.0.0.0" | サーバーホスト |
| `PORT` | int | 8000 | サーバーポート |
| `DEBUG` | bool | false | デバッグモード |
| `CORS_ORIGINS` | list | ["*"] | CORS許可オリジン |
| `LOG_LEVEL` | string | "INFO" | ログレベル |
| `AZURE_STORAGE_ACCOUNT_NAME` | string | "" | Azure Storage アカウント名 |
| `AZURE_STORAGE_ACCOUNT_KEY` | string | "" | Azure Storage アカウントキー |
| `AZURE_STORAGE_CONNECTION_STRING` | string | "" | Azure Storage 接続文字列 |
| `AZURE_STORAGE_CONTAINER_NAME` | string | "documents" | デフォルトコンテナ名 |

### 4.2 認証方式

Azure Blob Storage認証は以下の優先順位で選択される：

1. **接続文字列**: `AZURE_STORAGE_CONNECTION_STRING` が設定されている場合
2. **アカウントキー**: `AZURE_STORAGE_ACCOUNT_NAME` と `AZURE_STORAGE_ACCOUNT_KEY` が設定されている場合
3. **デフォルト認証**: `DefaultAzureCredential` を使用（マネージドID、Azure CLI等）

## 5. エラーハンドリング

### 5.1 エラーレスポンス形式
```json
{
  "detail": "エラーメッセージ"
}
```

### 5.2 エラーコード

| HTTPステータス | 説明 | 発生条件 |
|----------------|------|----------|
| 200 | 成功 | 正常処理 |
| 404 | Not Found | Blob が見つからない |
| 500 | Internal Server Error | サーバー内部エラー |
| 503 | Service Unavailable | サービス準備未完了 |

### 5.3 カスタム例外

- `BlobStorageError`: Blob Storage 操作の一般的なエラー
- `BlobNotFoundError`: Blob が見つからない場合のエラー
- `SasTokenError`: SASトークン生成・操作のエラー

## 6. ログ仕様

### 6.1 ログ形式
```
{timestamp} - {logger_name} - {level} - {message}
```

### 6.2 ログレベル
- **DEBUG**: 詳細なデバッグ情報
- **INFO**: 一般的な情報（デフォルト）
- **WARNING**: 警告
- **ERROR**: エラー

### 6.3 構造化ログ
各リクエストには以下の情報が付与される：
- `correlation_id`: リクエスト識別子
- `method`: HTTPメソッド
- `path`: リクエストパス
- `status_code`: レスポンスステータス
- `process_time`: 処理時間

### 6.4 レスポンスヘッダー
- `X-Correlation-ID`: リクエスト識別子
- `X-Process-Time`: 処理時間（秒）

## 7. セキュリティ仕様

### 7.1 CORS設定
- デフォルトで全オリジン許可（開発用）
- 本番環境では適切なオリジン制限が必要

### 7.2 Azure Blob Storage セキュリティ
- SASトークンベースの認証を使用
- 時間制限付きアクセス（デフォルト1時間、最大24時間）
- 読み取り専用権限でのアクセス制御
- 複数の認証方式をサポート（SAS優先、フォールバック対応）
- 最小権限の原則に基づくアクセス制御
- 接続情報の環境変数による管理

### 7.3 ログセキュリティ
- 機密情報のログ出力を回避
- 相関IDによるリクエスト追跡

## 8. パフォーマンス仕様

### 8.1 ストリーミング対応
- 大容量ファイルのメモリ効率的な配信
- BytesIO を使用したストリーム処理

### 8.2 非同期処理
- FastAPI の非同期処理による高並行性
- I/O バウンドなタスクの効率的な処理

## 9. 依存関係

### 9.1 主要ライブラリ

| ライブラリ | バージョン | 用途 |
|------------|------------|------|
| fastapi | >=0.115.13 | Web フレームワーク |
| uvicorn | >=0.34.3 | ASGI サーバー |
| pydantic | >=2.0.0,<3.0.0 | データ検証 |
| pydantic-settings | >=2.0.0 | 設定管理 |
| azure-storage-blob | >=12.19.0 | Azure Blob Storage |
| azure-identity | >=1.15.0 | Azure 認証 |
| httpx | >=0.25.0 | HTTP クライアント |

### 9.2 テスト用ライブラリ

| ライブラリ | バージョン | 用途 |
|------------|------------|------|
| pytest | >=7.0.0 | テストフレームワーク |
| pytest-asyncio | >=0.21.0 | 非同期テスト |
| pytest-cov | >=4.0.0 | カバレッジ測定 |
| httpx | >=0.25.0 | HTTPクライアント |
| pytest-mock | >=3.10.0 | モッキング |

## 10. デプロイメント仕様

### 10.1 Docker 対応
- Dockerfile による コンテナ化
- マルチステージビルド対応

### 10.2 Kubernetes 対応
- Health Check エンドポイント提供
- Readiness/Liveness プローブ対応

### 10.3 環境別設定
- 環境変数による設定管理
- .env ファイルサポート

## 11. 運用仕様

### 11.1 監視項目
- ヘルスチェックエンドポイント
- レスポンス時間
- エラー率
- システムリソース使用率

### 11.2 メトリクス
- リクエスト数
- レスポンス時間分布
- エラー発生率
- Blob Storage アクセス状況

### 11.3 ログ監視
- 構造化ログによる検索・分析
- 相関IDによるリクエスト追跡
- エラーパターンの検出

## 12. 今後の拡張予定

### 12.1 認証機能
- JWT トークン認証
- OAuth 2.0 / OpenID Connect
- マルチテナント認証

### 12.2 追加機能
- ファイルアップロード機能
- Blob Storage の書き込み操作
- ファイル変換機能

### 12.3 パフォーマンス向上
- キャッシュ機能
- CDN 統合
- データベース統合

### 12.4 運用機能
- メトリクス収集
- 分散トレーシング
- アラート機能

---

**最終更新**: 2025年6月25日  
**バージョン**: 1.1  
**作成者**: System Generated Documentation
