# GitHub Actions環境設定ガイド

本ドキュメントでは、Azure AI Foundry Agent Service のマルチテナント環境でGitHub ActionsによるCI/CDパイプラインを設定するための手順を説明します。

## 1. 前提条件

- Azure サブスクリプション
- GitHub リポジトリ管理者権限
- Azure CLI (ローカル設定用)

## 2. Azure設定

### 2.1 Service Principal作成

```bash
# Azure CLIでログイン
az login

# Service Principal作成
az ad sp create-for-rbac \
  --name "sp-fas-github-actions" \
  --role "Contributor" \
  --scopes "/subscriptions/{subscription-id}" \
  --json-auth

# 出力例:
# {
#   "clientId": "12345678-1234-1234-1234-123456789012",
#   "clientSecret": "your-client-secret",
#   "subscriptionId": "87654321-4321-4321-4321-210987654321",
#   "tenantId": "11111111-1111-1111-1111-111111111111"
# }
```

### 2.2 追加の役割割り当て

```bash
# Resource Group作成者権限
az role assignment create \
  --assignee {clientId} \
  --role "Resource Group Contributor" \
  --scope "/subscriptions/{subscription-id}"

# User Access Administrator (RBACロール割り当て用)
az role assignment create \
  --assignee {clientId} \
  --role "User Access Administrator" \
  --scope "/subscriptions/{subscription-id}"
```

## 3. GitHubリポジトリ設定

### 3.1 Repository Variables設定

GitHubリポジトリの **Settings > Secrets and variables > Actions** で以下のVariablesを設定：

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `AZURE_CLIENT_ID` | Service PrincipalのclientId | Azure認証用クライアントID |
| `AZURE_TENANT_ID` | Service PrincipalのtenantId | Azure テナントID |
| `AZURE_SUBSCRIPTION_ID` | Service PrincipalのsubscriptionId | Azure サブスクリプションID |

### 3.2 GitHub Environments設定

以下のEnvironmentsをリポジトリに作成します：

#### Pooled環境
- `pooled-dev`
- `pooled-staging` 
- `pooled-prod`

#### Silo環境
- `silo-contoso-dev`
- `silo-contoso-staging`
- `silo-contoso-prod`
- `silo-fabrikam-dev`
- `silo-fabrikam-staging`
- `silo-fabrikam-prod`

### 3.3 Environment Protection Rules

本番環境(`*-prod`)には以下の保護ルールを設定：

1. **Required reviewers**: 最低1名の承認者
2. **Wait timer**: デプロイ前に10分待機
3. **Deployment branches**: `main`ブランチのみ

## 4. ディレクトリ構造とパラメーターファイル

### 4.1 Pooled環境

```
pooled/
├── infra/
│   ├── main.bicep
│   ├── main.parameters.json          # デフォルトパラメーター
│   ├── main.parameters.dev.json      # 開発環境用
│   ├── main.parameters.staging.json  # ステージング環境用
│   └── main.parameters.prod.json     # 本番環境用
└── app/
```

### 4.2 Silo環境

```
silo/
├── infra/
│   ├── main.bicep
│   ├── main.parameters.json                    # デフォルトパラメーター
│   ├── main.parameters.dev.json                # 開発環境用
│   ├── main.parameters.staging.json            # ステージング環境用
│   ├── main.parameters.prod.json               # 本番環境用
│   ├── main.parameters.contoso.dev.json        # テナント固有パラメーター
│   ├── main.parameters.contoso.staging.json
│   ├── main.parameters.contoso.prod.json
│   ├── main.parameters.fabrikam.dev.json
│   ├── main.parameters.fabrikam.staging.json
│   └── main.parameters.fabrikam.prod.json
└── app/
```

## 5. パラメーターファイル例

### 5.1 Pooled環境パラメーター例

`pooled/infra/main.parameters.dev.json`:
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "projectName": {
      "value": "fas-pooled"
    },
    "environment": {
      "value": "dev"
    },
    "location": {
      "value": "Japan East"
    },
    "tenantConfigs": {
      "value": [
        {
          "id": "contoso",
          "name": "contoso",
          "displayName": "Contoso Corporation"
        },
        {
          "id": "fabrikam", 
          "name": "fabrikam",
          "displayName": "Fabrikam Inc."
        }
      ]
    },
    "containerCpuCore": {
      "value": "0.25"
    },
    "containerMemory": {
      "value": "0.5Gi"
    }
  }
}
```

### 5.2 Silo環境パラメーター例

`silo/infra/main.parameters.contoso.dev.json`:
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "projectName": {
      "value": "fas-silo"
    },
    "environment": {
      "value": "dev"
    },
    "tenantId": {
      "value": "contoso"
    },
    "tenantName": {
      "value": "Contoso Corporation"
    },
    "location": {
      "value": "Japan East"
    },
    "containerCpuCore": {
      "value": "0.5"
    },
    "containerMemory": {
      "value": "1Gi"
    }
  }
}
```

## 6. デプロイメント手順

### 6.1 自動デプロイメント

1. **プッシュによるトリガー**：
   - `pooled/infra/`に変更をプッシュ → Pooled環境デプロイ
   - `silo/infra/`に変更をプッシュ → Silo環境デプロイ

2. **手動トリガー**：
   - GitHub Actions タブから「Deploy Pooled Infrastructure」または「Deploy Silo Infrastructure」を選択
   - 環境とテナント（Siloの場合）を選択してワークフローを実行

### 6.2 デプロイメント確認

デプロイ完了後、以下を確認：

1. **Azure Portal**でリソースが作成されていることを確認
2. **GitHub Actions**のSummaryでデプロイ結果を確認
3. **Application Insights**でアプリケーションの動作を確認

## 7. トラブルシューティング

### 7.1 認証エラー

```
Error: The client '...' with object id '...' does not have authorization to perform action '...'
```

**解決方法**：
- Service Principalに適切な権限が割り当てられているか確認
- サブスクリプション、リソースグループレベルでの権限を確認

### 7.2 パラメーターファイルエラー

```
❌ No parameters file found
```

**解決方法**：
- 環境に対応するパラメーターファイルが存在するか確認
- ファイル名の命名規則を確認

### 7.3 Bicep検証エラー

```
❌ main.bicep validation failed
```

**解決方法**：
- ローカルで`az bicep build --file main.bicep`を実行してエラーを確認
- Bicepの構文とリソース定義を確認

## 8. セキュリティ考慮事項

1. **Secret管理**：
   - Service PrincipalのclientSecretはGitHub Secretsで管理（今回はFederated Identity使用）
   - パラメーターファイルには機密情報を含めない

2. **アクセス制御**：
   - 本番環境へのデプロイには承認者を設定
   - ブランチ保護ルールを設定

3. **監査**：
   - すべてのデプロイメントはGitHub Actionsでログが記録される
   - Azure Activity Logでリソース変更を追跡

## 9. 参考リンク

- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Azure Service Principal](https://docs.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
- [Azure Bicep](https://docs.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [GitHub Actions Azure Login](https://github.com/Azure/login)
