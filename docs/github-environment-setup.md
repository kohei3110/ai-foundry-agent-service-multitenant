# GitHub Environment設定ガイド

## 1. Environment構造

```
GitHub Repository
├── Environments
│   ├── dev
│   │   └── Secrets: AZURE_CREDENTIALS
│   ├── staging  
│   │   ├── Secrets: AZURE_CREDENTIALS
│   │   └── Protection Rules: Required reviewers
│   ├── prod
│   │   ├── Secrets: AZURE_CREDENTIALS
│   │   └── Protection Rules: Required reviewers, Wait timer
│   ├── silo-contoso-dev
│   ├── silo-contoso-staging
│   └── silo-contoso-prod
```

## 2. 環境固有の設定例

### Dev Environment
- **AZURE_CREDENTIALS**: `# {"clientId": "<GUID>", "clientSecret": "<GUID>", "subscriptionId": "<GUID>", "tenantId": "<GUID>"}`
- **LOCATION**: `Japan East`

### Staging Environment
- **AZURE_CREDENTIALS**: `# {"clientId": "<GUID>", "clientSecret": "<GUID>", "subscriptionId": "<GUID>", "tenantId": "<GUID>"}`
- **Protection Rules**: 1 required reviewer
- **Wait timer**: 5 minutes

### Production Environment
- **AZURE_CREDENTIALS**: `# {"clientId": "<GUID>", "clientSecret": "<GUID>", "subscriptionId": "<GUID>", "tenantId": "<GUID>"}`
- **Protection Rules**: 2 required reviewers
- **Wait timer**: 15 minutes
- **Deployment branches**: `main` only

## 3. ワークフローでの使用方法

```yaml
jobs:
  deploy:
    environment: 
      name: ${{ github.event.inputs.environment }}
      url: https://portal.azure.com
    steps:
      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
```

## 4. マルチテナント対応

### Silo Architecture
- Environment名: `silo-{tenant-id}-{environment}`
- 例: `silo-contoso-prod`, `silo-fabrikam-dev`

### Pooled Architecture  
- Environment名: `pooled-{environment}`
- 例: `pooled-prod`, `pooled-dev`

## 5. セキュリティ考慮事項

1. **Federated Identity (推奨)**
   - Service Principal + Client Secret の代わりに使用
   - より安全で管理が簡単

2. **Protection Rules**
   - 本番環境には必須
   - 承認者の設定
   - 待機時間の設定

3. **Branch Protection**
   - 本番環境は`main`ブランチのみ
   - 開発環境は制限なし

## 6. 運用のベストプラクティス

1. **Environment命名規則**
   - 一貫性のある命名
   - アーキテクチャタイプを含める

2. **変数の階層**
   - Repository Variables (共通設定)
   - Environment Variables (環境固有)
   - Secrets (機密情報)

3. **監査とログ**
   - Deployment履歴の追跡
   - 承認履歴の確認
   - リソース変更の追跡
