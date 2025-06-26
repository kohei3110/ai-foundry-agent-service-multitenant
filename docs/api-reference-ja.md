# Pooled Agent Service API リファレンス

## 概要

このドキュメントは、Pooled Agent Service の REST API の詳細なリファレンスです。すべてのエンドポイント、リクエスト/レスポンス形式、エラーハンドリングについて説明します。

## ベース URL

```
http://localhost:8000
```

## 認証

現在のバージョンでは認証は不要です。将来のバージョンでJWT認証が実装予定です。

## 共通ヘッダー

### リクエストヘッダー
- `Content-Type: application/json` (JSON ペイロードを送信する場合)
- `Accept: application/json`

### レスポンスヘッダー
- `X-Correlation-ID`: リクエストの一意識別子
- `X-Process-Time`: 処理時間（秒）
- `Content-Type`: レスポンスのMIMEタイプ

## エンドポイント詳細

### 1. ルートエンドポイント

#### サービス情報取得
サービスの基本情報とメタデータを取得します。

```http
GET /
```

**レスポンス**
- **Status Code**: 200 OK
- **Content-Type**: application/json

```json
{
  "message": "Pooled Agent Service is running",
  "architecture": "pooled",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

**レスポンスフィールド**
- `message` (string): サービス稼働メッセージ
- `architecture` (string): アーキテクチャタイプ
- `version` (string): サービスバージョン
- `docs` (string): API ドキュメントのパス
- `health` (string): ヘルスチェックエンドポイントのパス

---

### 2. ヘルスチェックエンドポイント

#### 基本ヘルスチェック
サービスの基本的な稼働状況を確認します。

```http
GET /health
```

**レスポンス**
- **Status Code**: 200 OK
- **Content-Type**: application/json

```json
{
  "status": "healthy",
  "timestamp": "2024-06-25T10:30:00Z",
  "service": "pooled-agent-service",
  "version": "0.1.0"
}
```

**レスポンスフィールド**
- `status` (string): ヘルス状態 ("healthy")
- `timestamp` (string): チェック実行時刻 (ISO 8601)
- `service` (string): サービス名
- `version` (string): サービスバージョン

#### Readiness チェック
Kubernetesのreadiness probeに対応したエンドポイントです。

```http
GET /health/ready
```

**レスポンス**
- **Status Code**: 200 OK (準備完了) / 503 Service Unavailable (準備未完了)
- **Content-Type**: application/json

```json
{
  "status": "ready",
  "timestamp": "2024-06-25T10:30:00Z",
  "checks": {
    "database": "ok",
    "external_apis": "ok"
  }
}
```

**レスポンスフィールド**
- `status` (string): 準備状態 ("ready" | "not_ready")
- `timestamp` (string): チェック実行時刻
- `checks` (object): 各依存サービスのチェック結果
  - `database` (string): データベース接続状態
  - `external_apis` (string): 外部API接続状態

#### Liveness チェック
Kubernetesのliveness probeに対応したエンドポイントです。

```http
GET /health/live
```

**レスポンス**
- **Status Code**: 200 OK
- **Content-Type**: application/json

```json
{
  "status": "alive",
  "timestamp": "2024-06-25T10:30:00Z",
  "uptime_seconds": 3600.25
}
```

**レスポンスフィールド**
- `status` (string): 生存状態 ("alive")
- `timestamp` (string): チェック実行時刻
- `uptime_seconds` (number): サービス稼働時間（秒）

---

### 3. Blob Storage エンドポイント

#### Blob コンテンツ取得
Azure Blob Storage からファイルコンテンツを取得します。

```http
GET /blobs/{blob_name}
```

**パスパラメータ**
- `blob_name` (string, required): 取得するBlobの名前

**クエリパラメータ**
- `container` (string, optional): コンテナ名（省略時はデフォルトコンテナを使用）
- `download` (boolean, optional): ダウンロード強制フラグ（デフォルト: false）

**リクエスト例**
```http
GET /blobs/document.pdf?container=my-container&download=true
```

**レスポンス**
- **Status Code**: 200 OK
- **Content-Type**: ファイルのMIMEタイプ

**レスポンスヘッダー**
- `Content-Length`: ファイルサイズ（バイト）
- `ETag`: ファイルのETag値
- `Last-Modified`: 最終更新日時
- `Content-Disposition`: ダウンロード指定時の添付ファイル名

**レスポンスボディ**
バイナリファイルコンテンツ

**エラーレスポンス**
```json
// 404 Not Found
{
  "detail": "Blob 'nonexistent.pdf' not found in container 'documents'"
}

// 500 Internal Server Error
{
  "detail": "Internal server error"
}
```

#### Blob ストリーミング取得
大容量ファイルをストリーミング配信で取得します。

```http
GET /blobs/{blob_name}/stream
```

**パスパラメータ**
- `blob_name` (string, required): 取得するBlobの名前

**クエリパラメータ**
- `container` (string, optional): コンテナ名

**レスポンス**
- **Status Code**: 200 OK
- **Content-Type**: ファイルのMIMEタイプ
- **Transfer-Encoding**: chunked

**特徴**
- メモリ効率的な大容量ファイル配信
- プログレッシブダウンロード対応

#### Blob メタデータ取得
Blobのメタデータ情報を取得します。

```http
GET /blobs/{blob_name}/metadata
```

**パスパラメータ**
- `blob_name` (string, required): 対象Blobの名前

**クエリパラメータ**
- `container` (string, optional): コンテナ名

**レスポンス**
- **Status Code**: 200 OK
- **Content-Type**: application/json

```json
{
  "name": "document.pdf",
  "container": "documents",
  "size": 1024000,
  "content_type": "application/pdf",
  "last_modified": "2024-06-25T10:30:00Z",
  "etag": "\"0x8D9A1B2C3D4E5F6\"",
  "metadata": {
    "author": "John Doe",
    "department": "Engineering"
  },
  "creation_time": "2024-06-25T09:00:00Z"
}
```

**レスポンスフィールド**
- `name` (string): Blob名
- `container` (string): コンテナ名
- `size` (number): ファイルサイズ（バイト）
- `content_type` (string): MIMEタイプ
- `last_modified` (string): 最終更新日時 (ISO 8601)
- `etag` (string): ETag値
- `metadata` (object): カスタムメタデータ
- `creation_time` (string): 作成日時 (ISO 8601)

#### Blob 存在確認
Blobの存在確認を行います（HEADリクエスト）。

```http
HEAD /blobs/{blob_name}
```

**パスパラメータ**
- `blob_name` (string, required): 確認するBlobの名前

**クエリパラメータ**
- `container` (string, optional): コンテナ名

**レスポンス**
- **Status Code**: 200 OK (存在) / 404 Not Found (存在しない)
- **Content-Length**: 0

**レスポンスヘッダー** (200の場合)
- `Content-Length`: ファイルサイズ
- `Content-Type`: ファイルのMIMEタイプ
- `ETag`: ETag値
- `Last-Modified`: 最終更新日時

---

## エラーハンドリング

### エラーレスポンス形式

すべてのエラーレスポンスは以下の形式で返されます：

```json
{
  "detail": "エラーの詳細メッセージ"
}
```

### HTTPステータスコード

| コード | 名称 | 説明 | 発生条件 |
|--------|------|------|----------|
| 200 | OK | 成功 | 正常にリクエストが処理された |
| 404 | Not Found | リソースが見つからない | 指定されたBlobが存在しない |
| 500 | Internal Server Error | サーバー内部エラー | Azure Storage接続エラーなど |
| 503 | Service Unavailable | サービス利用不可 | 依存サービスが利用できない（readinessチェック時） |

### エラーの種類

#### 404 Not Found
```json
{
  "detail": "Blob 'document.pdf' not found in container 'documents'"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

#### 503 Service Unavailable (readiness チェック時)
```json
{
  "status": "not_ready",
  "timestamp": "2024-06-25T10:30:00Z",
  "checks": {
    "database": "error",
    "external_apis": "ok"
  }
}
```

---

## 使用例

### cURL を使用した例

#### 基本ヘルスチェック
```bash
curl -X GET http://localhost:8000/health
```

#### Blob コンテンツ取得
```bash
curl -X GET http://localhost:8000/blobs/document.pdf
```

#### Blob ダウンロード
```bash
curl -X GET "http://localhost:8000/blobs/document.pdf?download=true" \
  -o downloaded_document.pdf
```

#### Blob メタデータ取得
```bash
curl -X GET http://localhost:8000/blobs/document.pdf/metadata
```

#### Blob 存在確認
```bash
curl -I http://localhost:8000/blobs/document.pdf
```

### JavaScript Fetch API を使用した例

#### サービス情報取得
```javascript
const response = await fetch('http://localhost:8000/');
const data = await response.json();
console.log(data);
```

#### Blob メタデータ取得
```javascript
const response = await fetch('http://localhost:8000/blobs/document.pdf/metadata');
if (response.ok) {
  const metadata = await response.json();
  console.log('File size:', metadata.size);
} else {
  console.error('Blob not found');
}
```

#### Blob ダウンロード
```javascript
const response = await fetch('http://localhost:8000/blobs/document.pdf?download=true');
if (response.ok) {
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'document.pdf';
  a.click();
} else {
  console.error('Download failed');
}
```

---

## レート制限

現在のバージョンではレート制限は実装されていません。将来のバージョンで実装予定です。

## バージョニング

APIのバージョニングは現在実装されていません。APIの変更がある場合は、新しいエンドポイントパスまたはヘッダーでバージョンを指定する予定です。

---

**最終更新**: 2024年6月25日  
**APIバージョン**: 0.1.0
