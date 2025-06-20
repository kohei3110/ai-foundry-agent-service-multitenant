# Pooled Multi-Tenant Application Specification

*Version 1.0 – 2025-06-20*

## 1. 概要

本仕様書は、Azure AI Foundry Agent Service (FAS) のPooled（共有）マルチテナント方式におけるPythonアプリケーションの設計・実装仕様を定義します。マルチテナント対応のセキュアなAgent Service実装を前提とします。

## 2. アプリケーション構成

### 2.1 アーキテクチャ概要

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │────│   API Gateway   │────│  Agent Service  │
│   (JWT Token)   │    │   (APIM + JWT)  │    │   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────┬─────────────┼─────────────────┐
                       │                 │             │                 │
                ┌─────────────┐  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                │ Cosmos DB   │  │   AI Search │ │ Blob Storage│ │  Key Vault  │
                │ (tenantId)  │  │ (tenantId)  │ │ (tenantId)  │ │ (per tenant)│
                └─────────────┘  └─────────────┘ └─────────────┘ └─────────────┘
```

### 2.2 技術スタック

| コンポーネント | 技術 | バージョン |
|-------------|------|-----------|
| **Runtime** | Python | 3.11+ |
| **Web Framework** | FastAPI | 0.104+ |
| **AI SDK** | Azure AI Agent Service | latest |
| **Database** | Azure Cosmos DB SDK | 4.5+ |
| **Search** | Azure Search SDK | 11.5+ |
| **Storage** | Azure Blob SDK | 12.19+ |
| **Security** | Azure Identity | 1.15+ |
| **Monitoring** | OpenTelemetry | 1.21+ |

## 3. プロジェクト構造

```
src/
├── main.py                     # FastAPI アプリケーションエントリーポイント
├── config/
│   ├── __init__.py
│   ├── settings.py             # 環境設定・構成管理
│   └── logging.py              # ログ設定
├── core/
│   ├── __init__.py
│   ├── security.py             # JWT認証・認可
│   ├── tenant.py               # テナント管理・コンテキスト
│   └── exceptions.py           # カスタム例外定義
├── models/
│   ├── __init__.py
│   ├── tenant.py               # テナントモデル
│   ├── agent.py                # エージェントモデル
│   └── message.py              # メッセージモデル
├── services/
│   ├── __init__.py
│   ├── agent_service.py        # FAS統合サービス
│   ├── cosmos_service.py       # Cosmos DB操作
│   ├── search_service.py       # AI Search操作
│   ├── storage_service.py      # Blob Storage操作
│   └── keyvault_service.py     # Key Vault操作
├── api/
│   ├── __init__.py
│   ├── deps.py                 # 依存性注入
│   ├── middleware.py           # ミドルウェア定義
│   └── routes/
│       ├── __init__.py
│       ├── agents.py           # エージェント操作API
│       ├── threads.py          # スレッド操作API
│       └── files.py            # ファイル操作API
├── utils/
│   ├── __init__.py
│   ├── telemetry.py           # テレメトリ・監視
│   └── validators.py          # データ検証
└── tests/
    ├── __init__.py
    ├── conftest.py            # テスト設定
    ├── unit/                  # ユニットテスト
    └── integration/           # 統合テスト
```

## 4. コア実装

### 4.1 設定管理 (`config/settings.py`)

```python
from pydantic import BaseSettings, Field
from typing import List, Optional
import os

class TenantConfig(BaseSettings):
    """テナント設定"""
    id: str
    name: str
    display_name: str
    cosmos_container_prefix: str = ""
    search_index_prefix: str = ""
    storage_container: str = ""
    keyvault_name: str = ""

class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # Azure AI Foundry
    ai_project_connection_string: str = Field(..., env="AI_PROJECT_CONNECTION_STRING")
    
    # Azure Cosmos DB
    cosmos_endpoint: str = Field(..., env="COSMOS_ENDPOINT")
    cosmos_database: str = Field("agents", env="COSMOS_DATABASE")
    
    # Azure AI Search
    search_endpoint: str = Field(..., env="SEARCH_ENDPOINT")
    
    # Azure Storage
    storage_account_url: str = Field(..., env="STORAGE_ACCOUNT_URL")
    
    # JWT設定
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("RS256", env="JWT_ALGORITHM")
    jwt_audience: str = Field(..., env="JWT_AUDIENCE")
    jwt_issuer: str = Field(..., env="JWT_ISSUER")
    
    # テナント設定
    tenants: List[TenantConfig] = Field(default_factory=list)
    
    # 監視設定
    applicationinsights_connection_string: Optional[str] = Field(None, env="APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    # セキュリティ設定
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    debug: bool = Field(False, env="DEBUG")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# グローバル設定インスタンス
settings = Settings()
```

### 4.2 テナントコンテキスト管理 (`core/tenant.py`)

```python
from contextvars import ContextVar
from typing import Optional, Dict, Any
from fastapi import HTTPException
from .exceptions import TenantNotFoundError

# テナントコンテキスト変数
current_tenant: ContextVar[Optional[str]] = ContextVar('current_tenant', default=None)

class TenantContext:
    """テナントコンテキスト管理"""
    
    @staticmethod
    def set_tenant(tenant_id: str) -> None:
        """現在のテナントIDを設定"""
        current_tenant.set(tenant_id)
    
    @staticmethod
    def get_tenant() -> str:
        """現在のテナントIDを取得"""
        tenant_id = current_tenant.get()
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant context not set")
        return tenant_id
    
    @staticmethod
    def get_tenant_config(tenant_id: str) -> Dict[str, Any]:
        """テナント設定を取得"""
        from config.settings import settings
        
        for tenant in settings.tenants:
            if tenant.id == tenant_id:
                return tenant.dict()
        
        raise TenantNotFoundError(f"Tenant {tenant_id} not found")
    
    @staticmethod
    def ensure_tenant_access(resource_tenant_id: str) -> None:
        """テナントアクセス権限チェック"""
        current_tenant_id = TenantContext.get_tenant()
        if current_tenant_id != resource_tenant_id:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied to tenant {resource_tenant_id}"
            )

# デコレータ
def require_tenant(func):
    """テナント必須デコレータ"""
    def wrapper(*args, **kwargs):
        TenantContext.get_tenant()  # テナントチェック
        return func(*args, **kwargs)
    return wrapper
```

### 4.3 JWT認証・認可 (`core/security.py`)

```python
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.settings import settings
from .tenant import TenantContext

security = HTTPBearer()

class JWTHandler:
    """JWT認証ハンドラ"""
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """JWTトークンをデコード"""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    @staticmethod
    def extract_tenant_id(payload: Dict[str, Any]) -> str:
        """JWTペイロードからテナントIDを抽出"""
        tenant_id = payload.get("extension_tenantId")
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant ID not found in token")
        return tenant_id
    
    @staticmethod
    def validate_tenant(tenant_id: str) -> None:
        """テナントIDの有効性検証"""
        valid_tenants = [tenant.id for tenant in settings.tenants]
        if tenant_id not in valid_tenants:
            raise HTTPException(status_code=401, detail=f"Invalid tenant: {tenant_id}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """現在のユーザー情報を取得"""
    token = credentials.credentials
    payload = JWTHandler.decode_token(token)
    
    # テナントIDを抽出・検証
    tenant_id = JWTHandler.extract_tenant_id(payload)
    JWTHandler.validate_tenant(tenant_id)
    
    # テナントコンテキストを設定
    TenantContext.set_tenant(tenant_id)
    
    return {
        "user_id": payload.get("sub"),
        "tenant_id": tenant_id,
        "roles": payload.get("roles", []),
        "email": payload.get("email"),
        "name": payload.get("name")
    }
```

### 4.4 Cosmos DB サービス (`services/cosmos_service.py`)

```python
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from typing import Dict, List, Any, Optional
from core.tenant import TenantContext, require_tenant
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class CosmosService:
    """Cosmos DB操作サービス"""
    
    def __init__(self):
        # Managed Identity認証
        credential = DefaultAzureCredential()
        self.client = CosmosClient(
            url=settings.cosmos_endpoint,
            credential=credential
        )
        self.database = self.client.get_database_client(settings.cosmos_database)
    
    def _get_container(self, container_name: str):
        """コンテナクライアントを取得"""
        return self.database.get_container_client(container_name)
    
    @require_tenant
    async def create_item(self, container_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """アイテム作成（テナントID必須）"""
        tenant_id = TenantContext.get_tenant()
        
        # テナントIDを強制設定
        item["tenantId"] = tenant_id
        
        container = self._get_container(container_name)
        
        try:
            response = container.create_item(
                body=item,
                partition_key=tenant_id
            )
            logger.info(f"Created item in {container_name} for tenant {tenant_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to create item in {container_name}: {e}")
            raise
    
    @require_tenant
    async def read_item(self, container_name: str, item_id: str) -> Optional[Dict[str, Any]]:
        """アイテム読み取り（テナント境界チェック）"""
        tenant_id = TenantContext.get_tenant()
        container = self._get_container(container_name)
        
        try:
            response = container.read_item(
                item=item_id,
                partition_key=tenant_id
            )
            
            # テナント境界チェック
            if response.get("tenantId") != tenant_id:
                logger.warning(f"Tenant boundary violation attempt: {tenant_id}")
                return None
            
            return response
        except Exception as e:
            logger.error(f"Failed to read item {item_id}: {e}")
            return None
    
    @require_tenant
    async def query_items(self, container_name: str, query: str, parameters: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """クエリ実行（テナントフィルター自動付与）"""
        tenant_id = TenantContext.get_tenant()
        container = self._get_container(container_name)
        
        # テナントフィルターを自動付与
        if "WHERE" in query.upper():
            query += f" AND c.tenantId = @tenantId"
        else:
            query += f" WHERE c.tenantId = @tenantId"
        
        # パラメータにテナントIDを追加
        if parameters is None:
            parameters = []
        parameters.append({"name": "@tenantId", "value": tenant_id})
        
        try:
            items = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=False  # テナント単一パーティション
            ))
            
            logger.info(f"Queried {len(items)} items from {container_name} for tenant {tenant_id}")
            return items
        except Exception as e:
            logger.error(f"Failed to query items: {e}")
            raise
    
    @require_tenant
    async def update_item(self, container_name: str, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """アイテム更新（テナント境界チェック）"""
        tenant_id = TenantContext.get_tenant()
        
        # 既存アイテムを取得してテナント確認
        existing_item = await self.read_item(container_name, item_id)
        if not existing_item:
            raise ValueError(f"Item {item_id} not found or access denied")
        
        # 更新データにテナントIDを強制設定
        updates["tenantId"] = tenant_id
        existing_item.update(updates)
        
        container = self._get_container(container_name)
        
        try:
            response = container.replace_item(
                item=item_id,
                body=existing_item,
                partition_key=tenant_id
            )
            logger.info(f"Updated item {item_id} in {container_name} for tenant {tenant_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to update item {item_id}: {e}")
            raise
    
    @require_tenant
    async def delete_item(self, container_name: str, item_id: str) -> None:
        """アイテム削除（テナント境界チェック）"""
        tenant_id = TenantContext.get_tenant()
        
        # 既存アイテムを取得してテナント確認
        existing_item = await self.read_item(container_name, item_id)
        if not existing_item:
            raise ValueError(f"Item {item_id} not found or access denied")
        
        container = self._get_container(container_name)
        
        try:
            container.delete_item(
                item=item_id,
                partition_key=tenant_id
            )
            logger.info(f"Deleted item {item_id} from {container_name} for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Failed to delete item {item_id}: {e}")
            raise
```

### 4.5 AI Search サービス (`services/search_service.py`)

```python
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.identity import DefaultAzureCredential
from typing import List, Dict, Any, Optional
from core.tenant import TenantContext, require_tenant
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class SearchService:
    """Azure AI Search操作サービス"""
    
    def __init__(self):
        credential = DefaultAzureCredential()
        self.endpoint = settings.search_endpoint
        self.credential = credential
    
    def _get_client(self, index_name: str) -> SearchClient:
        """Searchクライアントを取得"""
        return SearchClient(
            endpoint=self.endpoint,
            index_name=index_name,
            credential=self.credential
        )
    
    @require_tenant
    async def search_documents(
        self, 
        index_name: str, 
        search_text: str = "*",
        filter_expression: str = None,
        top: int = 50,
        select: List[str] = None
    ) -> List[Dict[str, Any]]:
        """ドキュメント検索（テナントフィルター自動付与）"""
        tenant_id = TenantContext.get_tenant()
        client = self._get_client(index_name)
        
        # テナントフィルターを自動付与
        tenant_filter = f"tenantId eq '{tenant_id}'"
        if filter_expression:
            combined_filter = f"({filter_expression}) and {tenant_filter}"
        else:
            combined_filter = tenant_filter
        
        try:
            results = client.search(
                search_text=search_text,
                filter=combined_filter,
                top=top,
                select=select
            )
            
            documents = [doc for doc in results]
            logger.info(f"Found {len(documents)} documents in {index_name} for tenant {tenant_id}")
            return documents
        except Exception as e:
            logger.error(f"Search failed in {index_name}: {e}")
            raise
    
    @require_tenant
    async def vector_search(
        self,
        index_name: str,
        vector: List[float],
        vector_field: str = "contentVector",
        k: int = 10,
        filter_expression: str = None
    ) -> List[Dict[str, Any]]:
        """ベクトル検索（テナントフィルター自動付与）"""
        tenant_id = TenantContext.get_tenant()
        client = self._get_client(index_name)
        
        # テナントフィルターを自動付与
        tenant_filter = f"tenantId eq '{tenant_id}'"
        if filter_expression:
            combined_filter = f"({filter_expression}) and {tenant_filter}"
        else:
            combined_filter = tenant_filter
        
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=k,
            fields=vector_field
        )
        
        try:
            results = client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=combined_filter,
                top=k
            )
            
            documents = [doc for doc in results]
            logger.info(f"Vector search found {len(documents)} documents in {index_name} for tenant {tenant_id}")
            return documents
        except Exception as e:
            logger.error(f"Vector search failed in {index_name}: {e}")
            raise
    
    @require_tenant
    async def upload_documents(self, index_name: str, documents: List[Dict[str, Any]]) -> None:
        """ドキュメントアップロード（テナントID自動付与）"""
        tenant_id = TenantContext.get_tenant()
        client = self._get_client(index_name)
        
        # 各ドキュメントにテナントIDを強制付与
        for doc in documents:
            doc["tenantId"] = tenant_id
        
        try:
            result = client.upload_documents(documents=documents)
            logger.info(f"Uploaded {len(documents)} documents to {index_name} for tenant {tenant_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to upload documents to {index_name}: {e}")
            raise
    
    @require_tenant
    async def delete_documents(self, index_name: str, document_keys: List[str]) -> None:
        """ドキュメント削除（テナント境界チェック）"""
        tenant_id = TenantContext.get_tenant()
        client = self._get_client(index_name)
        
        # 削除前にテナント所有権確認
        existing_docs = await self.search_documents(
            index_name=index_name,
            filter_expression=f"search.in(id, '{','.join(document_keys)}')",
            select=["id", "tenantId"]
        )
        
        valid_keys = [doc["id"] for doc in existing_docs if doc["tenantId"] == tenant_id]
        
        if len(valid_keys) != len(document_keys):
            logger.warning(f"Tenant {tenant_id} attempted to delete unauthorized documents")
            raise PermissionError("Some documents are not accessible to current tenant")
        
        try:
            documents_to_delete = [{"id": key} for key in valid_keys]
            result = client.delete_documents(documents=documents_to_delete)
            logger.info(f"Deleted {len(valid_keys)} documents from {index_name} for tenant {tenant_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete documents from {index_name}: {e}")
            raise
```

### 4.6 Agent Service (`services/agent_service.py`)

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from typing import Dict, List, Any, Optional
from core.tenant import TenantContext, require_tenant
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class AgentService:
    """AI Foundry Agent Service統合"""
    
    def __init__(self):
        credential = DefaultAzureCredential()
        self.client = AIProjectClient.from_connection_string(
            conn_str=settings.ai_project_connection_string,
            credential=credential
        )
    
    @require_tenant
    async def create_agent(self, name: str, instructions: str, model: str = "gpt-4") -> Dict[str, Any]:
        """エージェント作成（テナント情報付与）"""
        tenant_id = TenantContext.get_tenant()
        
        # エージェント名にテナント接頭辞を付与
        agent_name = f"{tenant_id}-{name}"
        
        try:
            agent = self.client.agents.create_agent(
                model=model,
                name=agent_name,
                instructions=instructions,
                metadata={
                    "tenantId": tenant_id,
                    "originalName": name
                }
            )
            
            logger.info(f"Created agent {agent.id} for tenant {tenant_id}")
            return agent.model_dump()
        except Exception as e:
            logger.error(f"Failed to create agent for tenant {tenant_id}: {e}")
            raise
    
    @require_tenant
    async def create_thread(self, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """スレッド作成（テナント情報付与）"""
        tenant_id = TenantContext.get_tenant()
        
        if metadata is None:
            metadata = {}
        
        # メタデータにテナント情報を強制追加
        metadata["tenantId"] = tenant_id
        
        try:
            thread = self.client.agents.create_thread(metadata=metadata)
            
            logger.info(f"Created thread {thread.id} for tenant {tenant_id}")
            return thread.model_dump()
        except Exception as e:
            logger.error(f"Failed to create thread for tenant {tenant_id}: {e}")
            raise
    
    @require_tenant
    async def create_message(
        self, 
        thread_id: str, 
        content: str, 
        role: str = "user",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """メッセージ作成（テナント境界チェック）"""
        tenant_id = TenantContext.get_tenant()
        
        # スレッド所有権確認
        thread = await self.get_thread(thread_id)
        if not thread or thread.get("metadata", {}).get("tenantId") != tenant_id:
            raise PermissionError(f"Thread {thread_id} not accessible to tenant {tenant_id}")
        
        if metadata is None:
            metadata = {}
        metadata["tenantId"] = tenant_id
        
        try:
            message = self.client.agents.create_message(
                thread_id=thread_id,
                role=role,
                content=content,
                metadata=metadata
            )
            
            logger.info(f"Created message {message.id} in thread {thread_id} for tenant {tenant_id}")
            return message.model_dump()
        except Exception as e:
            logger.error(f"Failed to create message for tenant {tenant_id}: {e}")
            raise
    
    @require_tenant
    async def create_run(
        self, 
        thread_id: str, 
        agent_id: str,
        instructions: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """実行作成（テナント境界チェック）"""
        tenant_id = TenantContext.get_tenant()
        
        # スレッドとエージェントの所有権確認
        thread = await self.get_thread(thread_id)
        if not thread or thread.get("metadata", {}).get("tenantId") != tenant_id:
            raise PermissionError(f"Thread {thread_id} not accessible to tenant {tenant_id}")
        
        agent = await self.get_agent(agent_id)
        if not agent or agent.get("metadata", {}).get("tenantId") != tenant_id:
            raise PermissionError(f"Agent {agent_id} not accessible to tenant {tenant_id}")
        
        if metadata is None:
            metadata = {}
        metadata["tenantId"] = tenant_id
        
        try:
            run = self.client.agents.create_run(
                thread_id=thread_id,
                assistant_id=agent_id,
                instructions=instructions,
                metadata=metadata
            )
            
            logger.info(f"Created run {run.id} for tenant {tenant_id}")
            return run.model_dump()
        except Exception as e:
            logger.error(f"Failed to create run for tenant {tenant_id}: {e}")
            raise
    
    @require_tenant
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """エージェント取得（テナント境界チェック）"""
        tenant_id = TenantContext.get_tenant()
        
        try:
            agent = self.client.agents.get_agent(agent_id)
            
            # テナント境界チェック
            if agent.metadata.get("tenantId") != tenant_id:
                logger.warning(f"Tenant {tenant_id} attempted to access agent {agent_id}")
                return None
            
            return agent.model_dump()
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None
    
    @require_tenant
    async def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """スレッド取得（テナント境界チェック）"""
        tenant_id = TenantContext.get_tenant()
        
        try:
            thread = self.client.agents.get_thread(thread_id)
            
            # テナント境界チェック
            if thread.metadata.get("tenantId") != tenant_id:
                logger.warning(f"Tenant {tenant_id} attempted to access thread {thread_id}")
                return None
            
            return thread.model_dump()
        except Exception as e:
            logger.error(f"Failed to get thread {thread_id}: {e}")
            return None
    
    @require_tenant
    async def list_agents(self, limit: int = 20, order: str = "desc") -> List[Dict[str, Any]]:
        """エージェント一覧（テナントフィルター）"""
        tenant_id = TenantContext.get_tenant()
        
        try:
            agents = self.client.agents.list_agents(limit=100, order=order)  # 多めに取得
            
            # テナントフィルター適用
            tenant_agents = [
                agent.model_dump() for agent in agents.data 
                if agent.metadata and agent.metadata.get("tenantId") == tenant_id
            ]
            
            # 制限適用
            return tenant_agents[:limit]
        except Exception as e:
            logger.error(f"Failed to list agents for tenant {tenant_id}: {e}")
            raise
```

## 5. API エンドポイント

### 5.1 エージェント操作API (`api/routes/agents.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from core.security import get_current_user
from services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])

class CreateAgentRequest(BaseModel):
    name: str
    instructions: str
    model: str = "gpt-4"

class CreateThreadRequest(BaseModel):
    metadata: Dict[str, Any] = {}

class CreateMessageRequest(BaseModel):
    content: str
    role: str = "user"
    metadata: Dict[str, Any] = {}

class CreateRunRequest(BaseModel):
    agent_id: str
    instructions: str = None
    metadata: Dict[str, Any] = {}

@router.post("/", response_model=Dict[str, Any])
async def create_agent(
    request: CreateAgentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """エージェント作成"""
    return await agent_service.create_agent(
        name=request.name,
        instructions=request.instructions,
        model=request.model
    )

@router.get("/{agent_id}", response_model=Dict[str, Any])
async def get_agent(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """エージェント取得"""
    agent = await agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.get("/", response_model=List[Dict[str, Any]])
async def list_agents(
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """エージェント一覧"""
    return await agent_service.list_agents(limit=limit)

@router.post("/threads", response_model=Dict[str, Any])
async def create_thread(
    request: CreateThreadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """スレッド作成"""
    return await agent_service.create_thread(metadata=request.metadata)

@router.post("/threads/{thread_id}/messages", response_model=Dict[str, Any])
async def create_message(
    thread_id: str,
    request: CreateMessageRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """メッセージ作成"""
    return await agent_service.create_message(
        thread_id=thread_id,
        content=request.content,
        role=request.role,
        metadata=request.metadata
    )

@router.post("/threads/{thread_id}/runs", response_model=Dict[str, Any])
async def create_run(
    thread_id: str,
    request: CreateRunRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """実行作成"""
    return await agent_service.create_run(
        thread_id=thread_id,
        agent_id=request.agent_id,
        instructions=request.instructions,
        metadata=request.metadata
    )
```

## 6. セキュリティ実装

### 6.1 ミドルウェア (`api/middleware.py`)

```python
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from core.tenant import TenantContext
import logging
import time
import uuid

logger = logging.getLogger(__name__)

class TenantLoggingMiddleware(BaseHTTPMiddleware):
    """テナント情報をログに追加"""
    
    async def dispatch(self, request: Request, call_next):
        # リクエストIDを生成
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # レスポンス情報をログ記録
            process_time = time.time() - start_time
            tenant_id = getattr(TenantContext, 'get_tenant', lambda: 'unknown')()
            
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "process_time": process_time
                }
            )
            
            # レスポンスヘッダーにリクエストIDを追加
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            tenant_id = getattr(TenantContext, 'get_tenant', lambda: 'unknown')()
            
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                    "method": request.method,
                    "url": str(request.url),
                    "process_time": process_time,
                    "error": str(e)
                }
            )
            raise

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """セキュリティヘッダー追加"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # セキュリティヘッダーを追加
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
```

## 7. 監視・テレメトリ

### 7.1 テレメトリ設定 (`utils/telemetry.py`)

```python
from opentelemetry import trace, metrics
from opentelemetry.exporter.azure.monitor import AzureMonitorTraceExporter, AzureMonitorMetricsExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.azure_core import AzureCoreInstrumentor
from config.settings import settings
from core.tenant import TenantContext
import logging

logger = logging.getLogger(__name__)

class TenantTelemetryProcessor:
    """テナント情報をテレメトリに追加"""
    
    def process(self, span):
        try:
            tenant_id = TenantContext.get_tenant()
            span.set_attribute("tenant.id", tenant_id)
        except:
            # テナントコンテキストが設定されていない場合は無視
            pass
        return span

def setup_telemetry(app):
    """テレメトリ設定"""
    
    if not settings.applicationinsights_connection_string:
        logger.warning("Application Insights connection string not configured")
        return
    
    # トレースプロバイダー設定
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Azure Monitor Exporter設定
    trace_exporter = AzureMonitorTraceExporter(
        connection_string=settings.applicationinsights_connection_string
    )
    
    # スパンプロセッサーにテナント情報を追加
    span_processor = trace.get_tracer_provider().add_span_processor(
        trace.BatchSpanProcessor(trace_exporter)
    )
    
    # 自動計測設定
    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()
    AzureCoreInstrumentor().instrument()
    
    logger.info("Telemetry configured successfully")

class TenantAwareLogger:
    """テナント対応ログ出力"""
    
    @staticmethod
    def info(message: str, **kwargs):
        try:
            tenant_id = TenantContext.get_tenant()
            logger.info(
                message, 
                extra={"tenant_id": tenant_id, **kwargs}
            )
        except:
            logger.info(message, extra=kwargs)
    
    @staticmethod
    def error(message: str, **kwargs):
        try:
            tenant_id = TenantContext.get_tenant()
            logger.error(
                message, 
                extra={"tenant_id": tenant_id, **kwargs}
            )
        except:
            logger.error(message, extra=kwargs)
    
    @staticmethod
    def warning(message: str, **kwargs):
        try:
            tenant_id = TenantContext.get_tenant()
            logger.warning(
                message, 
                extra={"tenant_id": tenant_id, **kwargs}
            )
        except:
            logger.warning(message, extra=kwargs)
```

## 8. テスト仕様

### 8.1 テナント境界テスト (`tests/integration/test_tenant_isolation.py`)

```python
import pytest
from fastapi.testclient import TestClient
from main import app
import jwt
from config.settings import settings

client = TestClient(app)

class TestTenantIsolation:
    """テナント境界分離テスト"""
    
    def create_jwt_token(self, tenant_id: str, user_id: str = "test-user") -> str:
        """テスト用JWTトークン作成"""
        payload = {
            "sub": user_id,
            "extension_tenantId": tenant_id,
            "roles": ["user"],
            "email": f"{user_id}@{tenant_id}.com",
            "name": f"Test User {tenant_id}"
        }
        
        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
    
    def test_cosmos_tenant_isolation(self):
        """Cosmos DB テナント分離テスト"""
        # Contoso テナントでアイテム作成
        contoso_token = self.create_jwt_token("contoso")
        response = client.post(
            "/cosmos/threads",
            json={"name": "Contoso Thread", "description": "Test thread"},
            headers={"Authorization": f"Bearer {contoso_token}"}
        )
        assert response.status_code == 200
        contoso_thread_id = response.json()["id"]
        
        # Fabrikam テナントで同じアイテムにアクセス試行
        fabrikam_token = self.create_jwt_token("fabrikam")
        response = client.get(
            f"/cosmos/threads/{contoso_thread_id}",
            headers={"Authorization": f"Bearer {fabrikam_token}"}
        )
        assert response.status_code == 403  # アクセス拒否
    
    def test_search_tenant_isolation(self):
        """AI Search テナント分離テスト"""
        # Contoso テナントでドキュメント登録
        contoso_token = self.create_jwt_token("contoso")
        response = client.post(
            "/search/documents",
            json=[{
                "id": "doc1",
                "content": "Contoso confidential document",
                "title": "Secret Plans"
            }],
            headers={"Authorization": f"Bearer {contoso_token}"}
        )
        assert response.status_code == 200
        
        # Fabrikam テナントで検索実行
        fabrikam_token = self.create_jwt_token("fabrikam")
        response = client.get(
            "/search/documents?query=confidential",
            headers={"Authorization": f"Bearer {fabrikam_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 0  # 結果なし
    
    def test_agent_tenant_isolation(self):
        """Agent テナント分離テスト"""
        # Contoso テナントでエージェント作成
        contoso_token = self.create_jwt_token("contoso")
        response = client.post(
            "/agents/",
            json={
                "name": "Contoso Assistant",
                "instructions": "You are a helpful assistant for Contoso.",
                "model": "gpt-4"
            },
            headers={"Authorization": f"Bearer {contoso_token}"}
        )
        assert response.status_code == 200
        contoso_agent_id = response.json()["id"]
        
        # Fabrikam テナントで同じエージェントにアクセス試行
        fabrikam_token = self.create_jwt_token("fabrikam")
        response = client.get(
            f"/agents/{contoso_agent_id}",
            headers={"Authorization": f"Bearer {fabrikam_token}"}
        )
        assert response.status_code == 404  # 見つからない（アクセス拒否）
    
    def test_cross_tenant_data_leakage(self):
        """クロステナントデータ漏洩テスト"""
        # 複数テナントでデータ作成
        tenants = ["contoso", "fabrikam", "northwind"]
        
        for tenant in tenants:
            token = self.create_jwt_token(tenant)
            
            # エージェント作成
            response = client.post(
                "/agents/",
                json={
                    "name": f"{tenant} Agent",
                    "instructions": f"You are {tenant}'s assistant.",
                    "model": "gpt-4"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
        
        # 各テナントでエージェント一覧取得（自分のもののみ表示されることを確認）
        for tenant in tenants:
            token = self.create_jwt_token(tenant)
            response = client.get(
                "/agents/",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            agents = response.json()
            
            # 自分のテナントのエージェントのみ表示されることを確認
            for agent in agents:
                assert agent["metadata"]["tenantId"] == tenant
    
    def test_unauthorized_access(self):
        """認証なしアクセステスト"""
        # トークンなしでAPIアクセス
        response = client.get("/agents/")
        assert response.status_code == 401
        
        # 無効なトークンでAPIアクセス
        response = client.get(
            "/agents/",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
    
    def test_invalid_tenant_access(self):
        """無効テナントアクセステスト"""
        # 存在しないテナントIDでトークン作成
        invalid_token = self.create_jwt_token("invalid-tenant")
        response = client.get(
            "/agents/",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401  # 無効テナント
```

## 9. デプロイメント要件

### 9.1 requirements.txt

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
azure-ai-projects==1.0.0b1
azure-cosmos==4.5.1
azure-search-documents==11.5.1
azure-storage-blob==12.19.0
azure-keyvault-secrets==4.7.0
azure-identity==1.15.0
azure-monitor-opentelemetry==1.2.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-requests==0.42b0
opentelemetry-instrumentation-azure-core==0.1.0
pydantic[email]==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
PyJWT[crypto]==2.8.0
python-jose[cryptography]==3.3.0
```

### 9.2 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# システムパッケージ更新
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードコピー
COPY src/ ./src/

# 実行ユーザー作成
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# アプリケーション起動
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 10. 運用ガイドライン

### 10.1 ログ監視クエリ (KQL)

```kql
// テナント別API呼び出し統計
traces
| where timestamp > ago(1h)
| where customDimensions has "tenant_id"
| summarize 
    requests = count(),
    unique_users = dcount(tostring(customDimensions.user_id)),
    avg_duration = avg(duration)
  by tenant_id = tostring(customDimensions.tenant_id)
| order by requests desc

// テナント境界違反検知
traces
| where timestamp > ago(24h)
| where message contains "boundary violation" or message contains "unauthorized"
| where customDimensions has "tenant_id"
| project 
    timestamp,
    tenant_id = tostring(customDimensions.tenant_id),
    message,
    operation_Name,
    customDimensions
| order by timestamp desc

// エラー率監視
requests
| where timestamp > ago(1h)
| summarize 
    total = count(),
    errors = countif(resultCode >= 400),
    error_rate = round(100.0 * countif(resultCode >= 400) / count(), 2)
  by tenant_id = tostring(customDimensions.tenant_id)
| where error_rate > 5  // 5%以上のエラー率でアラート
```

### 10.2 パフォーマンス最適化

- **Cosmos DB**: パーティションキー最適化、インデックスポリシー調整
- **AI Search**: フィルタークエリの最適化、インデックス分割
- **Blob Storage**: アクセスパターンに応じたホットティア設定
- **Application**: 非同期処理、コネクションプーリング、キャッシュ戦略

## 11. 関連仕様書

- [Pooled Infrastructure Specification](./pooled-infrastructure-spec.md)
- [Security & Compliance Guidelines](./security-guidelines.md)
- [API Documentation](./api-documentation.md)
- [Operation & Monitoring Procedures](./operations-procedures.md)
