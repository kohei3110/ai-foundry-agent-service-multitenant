#!/bin/bash
# setup-secrets.sh - Key Vaultにシークレットを設定するスクリプト

set -euo pipefail

# 環境変数の確認
if [ -z "${AZURE_ENV_NAME:-}" ]; then
    echo "エラー: 環境変数 AZURE_ENV_NAME が設定されていません"
    exit 1
fi

if [ -z "${AZURE_SUBSCRIPTION_ID:-}" ]; then
    echo "エラー: 環境変数 AZURE_SUBSCRIPTION_ID が設定されていません"
    exit 1
fi

if [ -z "${AZURE_RESOURCE_GROUP:-}" ]; then
    echo "エラー: 環境変数 AZURE_RESOURCE_GROUP が設定されていません"
    exit 1
fi

echo "=== Key Vault シークレット設定スクリプト ==="
echo "環境名: $AZURE_ENV_NAME"
echo "サブスクリプション: $AZURE_SUBSCRIPTION_ID"
echo "リソースグループ: $AZURE_RESOURCE_GROUP"

# リソース名を取得（ResourceTokenを計算）
RESOURCE_TOKEN=$(echo -n "$AZURE_RESOURCE_GROUP" | sha256sum | cut -c1-13)
KEY_VAULT_NAME="kv-${RESOURCE_TOKEN}"
COSMOS_ACCOUNT_NAME="cosmos-fas-pooled-dev-${RESOURCE_TOKEN}"
STORAGE_ACCOUNT_NAME="st${RESOURCE_TOKEN}dev"
SEARCH_SERVICE_NAME="srch-fas-pooled-dev-${RESOURCE_TOKEN}"

echo "Key Vault名: $KEY_VAULT_NAME"
echo "Cosmos DB名: $COSMOS_ACCOUNT_NAME"
echo "Storage Account名: $STORAGE_ACCOUNT_NAME"
echo "Search Service名: $SEARCH_SERVICE_NAME"

# Azure CLIが認証済みか確認
if ! az account show >/dev/null 2>&1; then
    echo "エラー: Azure CLIにサインインしてください (az login)"
    exit 1
fi

# リソースが存在するか確認
echo "リソースの存在確認中..."

if ! az keyvault show --name "$KEY_VAULT_NAME" --resource-group "$AZURE_RESOURCE_GROUP" >/dev/null 2>&1; then
    echo "エラー: Key Vault '$KEY_VAULT_NAME' が見つかりません"
    exit 1
fi

# Cosmos DB接続文字列を取得してKey Vaultに格納
echo "Cosmos DB接続文字列を設定中..."
if COSMOS_CONNECTION_STRING=$(az cosmosdb keys list \
  --name "$COSMOS_ACCOUNT_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --type connection-strings \
  --query "connectionStrings[0].connectionString" \
  --output tsv 2>/dev/null); then
  
  az keyvault secret set \
    --vault-name "$KEY_VAULT_NAME" \
    --name "cosmos-connection-string" \
    --value "$COSMOS_CONNECTION_STRING" \
    --output none
  echo "✓ Cosmos DB接続文字列を設定しました"
else
  echo "警告: Cosmos DB接続文字列の取得に失敗しました"
fi

# Storage Account接続文字列を取得してKey Vaultに格納
echo "Storage Account接続文字列を設定中..."
if STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name "$STORAGE_ACCOUNT_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query connectionString \
  --output tsv 2>/dev/null); then
  
  az keyvault secret set \
    --vault-name "$KEY_VAULT_NAME" \
    --name "storage-connection-string" \
    --value "$STORAGE_CONNECTION_STRING" \
    --output none
  echo "✓ Storage Account接続文字列を設定しました"
else
  echo "警告: Storage Account接続文字列の取得に失敗しました"
fi

# AI Search管理キーを取得してKey Vaultに格納
echo "AI Search APIキーを設定中..."
if SEARCH_API_KEY=$(az search admin-key show \
  --service-name "$SEARCH_SERVICE_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query primaryKey \
  --output tsv 2>/dev/null); then
  
  az keyvault secret set \
    --vault-name "$KEY_VAULT_NAME" \
    --name "search-api-key" \
    --value "$SEARCH_API_KEY" \
    --output none
  echo "✓ AI Search APIキーを設定しました"
else
  echo "警告: AI Search APIキーの取得に失敗しました"
fi

echo ""
echo "=== シークレット設定完了 ==="
echo "以下のシークレットがKey Vaultに設定されました:"
echo "- cosmos-connection-string"
echo "- storage-connection-string" 
echo "- search-api-key"
echo ""
echo "Key Vaultにアクセスするには、適切なアクセス許可が必要です。"
echo "詳細は以下のコマンドで確認できます:"
echo "az keyvault secret list --vault-name $KEY_VAULT_NAME"
