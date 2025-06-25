# Pooled Application CI/CD Setup Guide

このドキュメントでは、pooled/appディレクトリのPythonコンテナアプリケーション用CI/CDパイプラインの設定と使用方法について説明します。

## 概要

GitHub Actionsワークフロー `deploy-pooled-app.yml` は以下の機能を提供します：

- **自動トリガー**: pooled/appディレクトリの変更時に自動実行
- **テスト**: 単体テストと統合テストの実行
- **Docker**: コンテナイメージのビルドとAzure Container Registryへのプッシュ
- **デプロイ**: Azure Container Appsへのデプロイ
- **多環境対応**: dev, staging, prodの各環境に対応

## トリガー条件

### 自動トリガー
1. **プッシュ**: 以下のブランチにプッシュされた場合
   - `main` → 本番環境(prod)
   - `develop` → ステージング環境(staging)  
   - `feature/**`, `hotfix/**` → 開発環境(dev)

2. **プルリクエスト**: main/developブランチへのPR作成時
   - ビルドとテストのみ実行（デプロイは行わない）

### 手動トリガー
GitHub Actionsタブから手動実行可能：
- 環境選択（dev/staging/prod）
- 強制デプロイオプション

## 前提条件

### 1. インフラストラクチャの事前デプロイ
アプリケーションデプロイ前に、以下のリソースが作成されている必要があります：

```bash
# Pooledインフラをデプロイ
cd pooled/infra
az deployment group create \
  --resource-group "rg-fas-pooled-{environment}" \
  --template-file "main.bicep" \
  --parameters "@main.parameters.{environment}.json"
```

必要なリソース：
- Azure Container Registry: `acrfaspooled{environment}`
- Azure Container Apps Environment
- Azure Container App: `ca-fas-pooled-{environment}`

### 2. GitHub環境設定
以下のGitHub環境が設定されている必要があります：
- `pooled-dev`
- `pooled-staging`
- `pooled-prod`

### 3. Azure認証設定
GitHub Variables（Repository Settings > Secrets and variables > Actions）：
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

## ワークフローの流れ

### 1. Environment Detection
```yaml
detect-environment:
  # ブランチ名からデプロイ環境を自動判定
  # イメージタグの生成
  # 変更検出による条件付きデプロイ
```

### 2. Application Testing
```yaml
test-application:
  # Python 3.12セットアップ
  # uvによる依存関係インストール
  # リンティング（設定済みの場合）
  # 単体テスト（カバレッジレポート付き）
  # 統合テスト
```

### 3. Docker Build & Push
```yaml
build-and-push-image:
  # Azure Container Registryへのログイン
  # マルチプラットフォームビルド（linux/amd64）
  # イメージキャッシュ活用
  # 脆弱性スキャン
```

### 4. Application Deployment
```yaml
deploy-application:
  # Container Appの更新
  # 環境変数の設定
  # デプロイ検証
  # ヘルスチェック
```

## イメージタグの命名規則

| トリガー | タグ形式 | 例 |
|---------|---------|-----|
| main branch | `prod-{commit-hash}` | `prod-a1b2c3d4` |
| develop branch | `staging-{commit-hash}` | `staging-a1b2c3d4` |
| feature branch | `dev-{commit-hash}` | `dev-a1b2c3d4` |
| Pull Request | `pr-{number}-{commit-hash}` | `pr-42-a1b2c3d4` |

## アプリケーション設定

### 環境変数
デプロイ時に以下の環境変数が自動設定されます：
- `ENVIRONMENT`: デプロイ先環境（dev/staging/prod）
- `AZURE_CLIENT_ID`: マネージドアイデンティティのクライアントID

### ヘルスチェック
アプリケーションは `/health` エンドポイントを提供する必要があります：
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

## トラブルシューティング

### 1. ビルド失敗
```bash
# ローカルでのテスト実行
cd pooled/app
uv sync
uv run pytest tests/ -v
```

### 2. イメージプッシュ失敗
- Azure Container Registryが存在することを確認
- Service Principalに適切な権限があることを確認

### 3. デプロイ失敗
```bash
# Container Appのログ確認
az containerapp logs show \
  --name "ca-fas-pooled-{environment}" \
  --resource-group "rg-fas-pooled-{environment}"
```

### 4. ヘルスチェック失敗
- アプリケーションが正常に起動していることを確認
- `/health` エンドポイントが実装されていることを確認

## ベストプラクティス

### 1. テスト
- 全てのプルリクエストでテストを実行
- カバレッジレポートを確認
- 統合テストを適切に実装

### 2. セキュリティ
- 定期的なイメージ脆弱性スキャン
- 最小権限の原則に従った権限設定
- 機密情報はKey Vaultまたはシークレットで管理

### 3. パフォーマンス
- Docker Buildxキャッシュの活用
- マルチステージビルドの検討
- イメージサイズの最適化

### 4. 監視
- Application Insightsの活用
- ログ集約とアラート設定
- メトリクス監視

## 参考リンク

- [Azure Container Apps](https://docs.microsoft.com/en-us/azure/container-apps/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Docker Buildx](https://docs.docker.com/buildx/)
- [Azure Container Registry](https://docs.microsoft.com/en-us/azure/container-registry/)
