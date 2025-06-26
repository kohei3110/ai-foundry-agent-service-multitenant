# Pooled Multi-Tenant Application Specification

*Version 1.0 – 2025-06-20*

## 1. Overview

This specification defines the design and implementation requirements for Python applications in the Pooled (shared) multi-tenant approach of Azure AI Foundry Agent Service (FAS). It assumes a secure Agent Service implementation with multi-tenant support.

## 2. Application Architecture

### 2.1 Architecture Overview

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

### 2.2 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Runtime** | Python | 3.11+ |
| **Web Framework** | FastAPI | 0.104+ |
| **AI SDK** | Azure AI Agent Service | latest |
| **Database** | Azure Cosmos DB SDK | 4.5+ |
| **Search** | Azure Search SDK | 11.5+ |
| **Storage** | Azure Blob SDK | 12.19+ |
| **Security** | Azure Identity | 1.15+ |
| **Monitoring** | OpenTelemetry | 1.21+ |

## 3. Project Structure

```
src/
├── main.py                     # FastAPI application entry point
├── config/
│   ├── __init__.py
│   ├── settings.py             # Environment settings and configuration management
│   └── logging.py              # Logging configuration
├── core/
│   ├── __init__.py
│   ├── security.py             # JWT authentication and authorization
│   ├── tenant.py               # Tenant management and context
│   └── exceptions.py           # Custom exception definitions
├── models/
│   ├── __init__.py
│   ├── tenant.py               # Tenant models
│   ├── agent.py                # Agent models
│   └── message.py              # Message models
├── services/
│   ├── __init__.py
│   ├── agent_service.py        # FAS integration service
│   ├── cosmos_service.py       # Cosmos DB operations
│   ├── search_service.py       # AI Search operations
│   ├── storage_service.py      # Blob Storage operations
│   └── keyvault_service.py     # Key Vault operations
├── api/
│   ├── __init__.py
│   ├── deps.py                 # Dependency injection
│   ├── middleware.py           # Middleware definitions
│   └── routes/
│       ├── __init__.py
│       ├── agents.py           # Agent operation APIs
│       ├── threads.py          # Thread operation APIs
│       └── files.py            # File operation APIs
├── utils/
│   ├── __init__.py
│   ├── telemetry.py           # Telemetry and monitoring
│   └── validators.py          # Data validation
└── tests/
    ├── __init__.py
    ├── conftest.py            # Test configuration
    ├── unit/                  # Unit tests
    └── integration/           # Integration tests
```

## 4. Core Implementation

### 4.1 Configuration Management (`config/settings.py`)

```python
from pydantic import BaseSettings, Field
from typing import List, Optional
import os

class TenantConfig(BaseSettings):
    """Tenant configuration"""
    id: str
    name: str
    display_name: str
    cosmos_container_prefix: str = ""
    search_index_prefix: str = ""
    storage_container: str = ""
    keyvault_name: str = ""

class Settings(BaseSettings):
    """Application settings"""
    
    # Azure AI Foundry
    ai_project_connection_string: str = Field(..., env="AI_PROJECT_CONNECTION_STRING")
    
    # Azure Cosmos DB
    cosmos_endpoint: str = Field(..., env="COSMOS_ENDPOINT")
    cosmos_database: str = Field("agents", env="COSMOS_DATABASE")
    
    # Azure AI Search
    search_endpoint: str = Field(..., env="SEARCH_ENDPOINT")
    
    # Azure Storage
    storage_account_url: str = Field(..., env="STORAGE_ACCOUNT_URL")
    
    # JWT settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("RS256", env="JWT_ALGORITHM")
    jwt_audience: str = Field(..., env="JWT_AUDIENCE")
    jwt_issuer: str = Field(..., env="JWT_ISSUER")
    
    # Tenant settings
    tenants: List[TenantConfig] = Field(default_factory=list)
    
    # Monitoring settings
    applicationinsights_connection_string: Optional[str] = Field(None, env="APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    # Security settings
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    debug: bool = Field(False, env="DEBUG")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
```

### 4.2 Tenant Context Management (`core/tenant.py`)

```python
from contextvars import ContextVar
from typing import Optional, Dict, Any
from fastapi import HTTPException
from .exceptions import TenantNotFoundError

# Tenant context variable
current_tenant: ContextVar[Optional[str]] = ContextVar('current_tenant', default=None)

class TenantContext:
    """Tenant context management"""
    
    @staticmethod
    def set_tenant(tenant_id: str) -> None:
        """Set current tenant ID"""
        current_tenant.set(tenant_id)
    
    @staticmethod
    def get_tenant() -> str:
        """Get current tenant ID"""
        tenant_id = current_tenant.get()
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant context not set")
        return tenant_id
    
    @staticmethod
    def get_tenant_config(tenant_id: str) -> Dict[str, Any]:
        """Get tenant configuration"""
        from config.settings import settings
        
        for tenant in settings.tenants:
            if tenant.id == tenant_id:
                return tenant.dict()
        
        raise TenantNotFoundError(f"Tenant {tenant_id} not found")
    
    @staticmethod
    def ensure_tenant_access(resource_tenant_id: str) -> None:
        """Check tenant access permissions"""
        current_tenant_id = TenantContext.get_tenant()
        if current_tenant_id != resource_tenant_id:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied to tenant {resource_tenant_id}"
            )

# Decorator
def require_tenant(func):
    """Tenant required decorator"""
    def wrapper(*args, **kwargs):
        TenantContext.get_tenant()  # Tenant check
        return func(*args, **kwargs)
    return wrapper
```

### 4.3 JWT Authentication and Authorization (`core/security.py`)

```python
import jwt
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.settings import settings
from .tenant import TenantContext

security = HTTPBearer()

class JWTHandler:
    """JWT authentication handler"""
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decode JWT token"""
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
        """Extract tenant ID from JWT payload"""
        tenant_id = payload.get("extension_tenantId")
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant ID not found in token")
        return tenant_id
    
    @staticmethod
    def validate_tenant(tenant_id: str) -> None:
        """Validate tenant ID"""
        valid_tenants = [tenant.id for tenant in settings.tenants]
        if tenant_id not in valid_tenants:
            raise HTTPException(status_code=401, detail=f"Invalid tenant: {tenant_id}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user information"""
    token = credentials.credentials
    payload = JWTHandler.decode_token(token)
    
    # Extract and validate tenant ID
    tenant_id = JWTHandler.extract_tenant_id(payload)
    JWTHandler.validate_tenant(tenant_id)
    
    # Set tenant context
    TenantContext.set_tenant(tenant_id)
    
    return {
        "user_id": payload.get("sub"),
        "tenant_id": tenant_id,
        "roles": payload.get("roles", []),
        "email": payload.get("email"),
        "name": payload.get("name")
    }
```

### 4.4 Cosmos DB Service (`services/cosmos_service.py`)

```python
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from typing import Dict, List, Any, Optional
from core.tenant import TenantContext, require_tenant
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class CosmosService:
    """Cosmos DB operations service"""
    
    def __init__(self):
        # Managed Identity authentication
        credential = DefaultAzureCredential()
        self.client = CosmosClient(
            url=settings.cosmos_endpoint,
            credential=credential
        )
        self.database = self.client.get_database_client(settings.cosmos_database)
    
    def _get_container(self, container_name: str):
        """Get container client"""
        return self.database.get_container_client(container_name)
    
    @require_tenant
    async def create_item(self, container_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Create item (tenant ID required)"""
        tenant_id = TenantContext.get_tenant()
        
        # Force set tenant ID
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
        """Read item (tenant boundary check)"""
        tenant_id = TenantContext.get_tenant()
        container = self._get_container(container_name)
        
        try:
            response = container.read_item(
                item=item_id,
                partition_key=tenant_id
            )
            
            # Tenant boundary check
            if response.get("tenantId") != tenant_id:
                logger.warning(f"Tenant boundary violation attempt: {tenant_id}")
                return None
            
            return response
        except Exception as e:
            logger.error(f"Failed to read item {item_id}: {e}")
            return None
    
    @require_tenant
    async def query_items(self, container_name: str, query: str, parameters: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query (automatic tenant filter)"""
        tenant_id = TenantContext.get_tenant()
        container = self._get_container(container_name)
        
        # Automatically add tenant filter
        if "WHERE" in query.upper():
            query += f" AND c.tenantId = @tenantId"
        else:
            query += f" WHERE c.tenantId = @tenantId"
        
        # Add tenant ID to parameters
        if parameters is None:
            parameters = []
        parameters.append({"name": "@tenantId", "value": tenant_id})
        
        try:
            items = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=False  # Single tenant partition
            ))
            
            logger.info(f"Queried {len(items)} items from {container_name} for tenant {tenant_id}")
            return items
        except Exception as e:
            logger.error(f"Failed to query items: {e}")
            raise
    
    @require_tenant
    async def update_item(self, container_name: str, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update item (tenant boundary check)"""
        tenant_id = TenantContext.get_tenant()
        
        # Get existing item and check tenant
        existing_item = await self.read_item(container_name, item_id)
        if not existing_item:
            raise ValueError(f"Item {item_id} not found or access denied")
        
        # Force set tenant ID in updates
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
        """Delete item (tenant boundary check)"""
        tenant_id = TenantContext.get_tenant()
        
        # Get existing item and check tenant
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

### 4.5 AI Search Service (`services/search_service.py`)

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
    """Azure AI Search operations service"""
    
    def __init__(self):
        credential = DefaultAzureCredential()
        self.endpoint = settings.search_endpoint
        self.credential = credential
    
    def _get_client(self, index_name: str) -> SearchClient:
        """Get Search client"""
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
        """Search documents (automatic tenant filter)"""
        tenant_id = TenantContext.get_tenant()
        client = self._get_client(index_name)
        
        # Automatically add tenant filter
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
        """Vector search (automatic tenant filter)"""
        tenant_id = TenantContext.get_tenant()
        client = self._get_client(index_name)
        
        # Automatically add tenant filter
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
        """Upload documents (automatic tenant ID assignment)"""
        tenant_id = TenantContext.get_tenant()
        client = self._get_client(index_name)
        
        # Force add tenant ID to each document
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
        """Delete documents (tenant boundary check)"""
        tenant_id = TenantContext.get_tenant()
        client = self._get_client(index_name)
        
        # Check tenant ownership before deletion
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
    """AI Foundry Agent Service integration"""
    
    def __init__(self):
        credential = DefaultAzureCredential()
        self.client = AIProjectClient.from_connection_string(
            conn_str=settings.ai_project_connection_string,
            credential=credential
        )
    
    @require_tenant
    async def create_agent(self, name: str, instructions: str, model: str = "gpt-4") -> Dict[str, Any]:
        """Create agent (tenant information assignment)"""
        tenant_id = TenantContext.get_tenant()
        
        # Add tenant prefix to agent name
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
        """Create thread (tenant information assignment)"""
        tenant_id = TenantContext.get_tenant()
        
        if metadata is None:
            metadata = {}
        
        # Force add tenant information to metadata
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
        """Create message (tenant boundary check)"""
        tenant_id = TenantContext.get_tenant()
        
        # Check thread ownership
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
        """Create run (tenant boundary check)"""
        tenant_id = TenantContext.get_tenant()
        
        # Check thread and agent ownership
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
        """Get agent (tenant boundary check)"""
        tenant_id = TenantContext.get_tenant()
        
        try:
            agent = self.client.agents.get_agent(agent_id)
            
            # Tenant boundary check
            if agent.metadata.get("tenantId") != tenant_id:
                logger.warning(f"Tenant {tenant_id} attempted to access agent {agent_id}")
                return None
            
            return agent.model_dump()
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None
    
    @require_tenant
    async def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get thread (tenant boundary check)"""
        tenant_id = TenantContext.get_tenant()
        
        try:
            thread = self.client.agents.get_thread(thread_id)
            
            # Tenant boundary check
            if thread.metadata.get("tenantId") != tenant_id:
                logger.warning(f"Tenant {tenant_id} attempted to access thread {thread_id}")
                return None
            
            return thread.model_dump()
        except Exception as e:
            logger.error(f"Failed to get thread {thread_id}: {e}")
            return None
    
    @require_tenant
    async def list_agents(self, limit: int = 20, order: str = "desc") -> List[Dict[str, Any]]:
        """List agents (tenant filter)"""
        tenant_id = TenantContext.get_tenant()
        
        try:
            agents = self.client.agents.list_agents(limit=100, order=order)  # Fetch more
            
            # Apply tenant filter
            tenant_agents = [
                agent.model_dump() for agent in agents.data 
                if agent.metadata and agent.metadata.get("tenantId") == tenant_id
            ]
            
            # Apply limit
            return tenant_agents[:limit]
        except Exception as e:
            logger.error(f"Failed to list agents for tenant {tenant_id}: {e}")
            raise
```

## 5. API Endpoints

### 5.1 Agent Operations API (`api/routes/agents.py`)

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
    """Create agent"""
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
    """Get agent"""
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
    """List agents"""
    return await agent_service.list_agents(limit=limit)

@router.post("/threads", response_model=Dict[str, Any])
async def create_thread(
    request: CreateThreadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """Create thread"""
    return await agent_service.create_thread(metadata=request.metadata)

@router.post("/threads/{thread_id}/messages", response_model=Dict[str, Any])
async def create_message(
    thread_id: str,
    request: CreateMessageRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """Create message"""
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
    """Create run"""
    return await agent_service.create_run(
        thread_id=thread_id,
        agent_id=request.agent_id,
        instructions=request.instructions,
        metadata=request.metadata
    )
```

## 6. Security Implementation

### 6.1 Middleware (`api/middleware.py`)

```python
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from core.tenant import TenantContext
import logging
import time
import uuid

logger = logging.getLogger(__name__)

class TenantLoggingMiddleware(BaseHTTPMiddleware):
    """Add tenant information to logs"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log response information
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
            
            # Add request ID to response headers
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
    """Add security headers"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
```

## 7. Monitoring and Telemetry

### 7.1 Telemetry Configuration (`utils/telemetry.py`)

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
    """Add tenant information to telemetry"""
    
    def process(self, span):
        try:
            tenant_id = TenantContext.get_tenant()
            span.set_attribute("tenant.id", tenant_id)
        except:
            # Ignore if tenant context is not set
            pass
        return span

def setup_telemetry(app):
    """Configure telemetry"""
    
    if not settings.applicationinsights_connection_string:
        logger.warning("Application Insights connection string not configured")
        return
    
    # Configure trace provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Configure Azure Monitor Exporter
    trace_exporter = AzureMonitorTraceExporter(
        connection_string=settings.applicationinsights_connection_string
    )
    
    # Add tenant information to span processor
    span_processor = trace.get_tracer_provider().add_span_processor(
        trace.BatchSpanProcessor(trace_exporter)
    )
    
    # Configure auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()
    AzureCoreInstrumentor().instrument()
    
    logger.info("Telemetry configured successfully")

class TenantAwareLogger:
    """Tenant-aware log output"""
    
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

## 8. Test Specifications

### 8.1 Tenant Boundary Tests (`tests/integration/test_tenant_isolation.py`)

```python
import pytest
from fastapi.testclient import TestClient
from main import app
import jwt
from config.settings import settings

client = TestClient(app)

class TestTenantIsolation:
    """Tenant boundary isolation tests"""
    
    def create_jwt_token(self, tenant_id: str, user_id: str = "test-user") -> str:
        """Create test JWT token"""
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
        """Cosmos DB tenant isolation test"""
        # Create item with Contoso tenant
        contoso_token = self.create_jwt_token("contoso")
        response = client.post(
            "/cosmos/threads",
            json={"name": "Contoso Thread", "description": "Test thread"},
            headers={"Authorization": f"Bearer {contoso_token}"}
        )
        assert response.status_code == 200
        contoso_thread_id = response.json()["id"]
        
        # Try to access same item with Fabrikam tenant
        fabrikam_token = self.create_jwt_token("fabrikam")
        response = client.get(
            f"/cosmos/threads/{contoso_thread_id}",
            headers={"Authorization": f"Bearer {fabrikam_token}"}
        )
        assert response.status_code == 403  # Access denied
    
    def test_search_tenant_isolation(self):
        """AI Search tenant isolation test"""
        # Register document with Contoso tenant
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
        
        # Execute search with Fabrikam tenant
        fabrikam_token = self.create_jwt_token("fabrikam")
        response = client.get(
            "/search/documents?query=confidential",
            headers={"Authorization": f"Bearer {fabrikam_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 0  # No results
    
    def test_agent_tenant_isolation(self):
        """Agent tenant isolation test"""
        # Create agent with Contoso tenant
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
        
        # Try to access same agent with Fabrikam tenant
        fabrikam_token = self.create_jwt_token("fabrikam")
        response = client.get(
            f"/agents/{contoso_agent_id}",
            headers={"Authorization": f"Bearer {fabrikam_token}"}
        )
        assert response.status_code == 404  # Not found (access denied)
    
    def test_cross_tenant_data_leakage(self):
        """Cross-tenant data leakage test"""
        # Create data with multiple tenants
        tenants = ["contoso", "fabrikam", "northwind"]
        
        for tenant in tenants:
            token = self.create_jwt_token(tenant)
            
            # Create agent
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
        
        # Get agent list for each tenant (verify only own agents are shown)
        for tenant in tenants:
            token = self.create_jwt_token(tenant)
            response = client.get(
                "/agents/",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            agents = response.json()
            
            # Verify only own tenant's agents are shown
            for agent in agents:
                assert agent["metadata"]["tenantId"] == tenant
    
    def test_unauthorized_access(self):
        """Unauthorized access test"""
        # API access without token
        response = client.get("/agents/")
        assert response.status_code == 401
        
        # API access with invalid token
        response = client.get(
            "/agents/",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
    
    def test_invalid_tenant_access(self):
        """Invalid tenant access test"""
        # Create token with non-existent tenant ID
        invalid_token = self.create_jwt_token("invalid-tenant")
        response = client.get(
            "/agents/",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401  # Invalid tenant
```

## 9. Deployment Requirements

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

# Update system packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create execution user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 10. Operational Guidelines

### 10.1 Log Monitoring Queries (KQL)

```kql
// Tenant-specific API call statistics
traces
| where timestamp > ago(1h)
| where customDimensions has "tenant_id"
| summarize 
    requests = count(),
    unique_users = dcount(tostring(customDimensions.user_id)),
    avg_duration = avg(duration)
  by tenant_id = tostring(customDimensions.tenant_id)
| order by requests desc

// Tenant boundary violation detection
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

// Error rate monitoring
requests
| where timestamp > ago(1h)
| summarize 
    total = count(),
    errors = countif(resultCode >= 400),
    error_rate = round(100.0 * countif(resultCode >= 400) / count(), 2)
  by tenant_id = tostring(customDimensions.tenant_id)
| where error_rate > 5  // Alert for error rates above 5%
```

### 10.2 Performance Optimization

- **Cosmos DB**: Partition key optimization, index policy tuning
- **AI Search**: Filter query optimization, index partitioning
- **Blob Storage**: Hot tier configuration based on access patterns
- **Application**: Asynchronous processing, connection pooling, caching strategies

## 11. Related Specifications

- [Pooled Infrastructure Specification](./pooled-infrastructure-spec.md)
- [Security & Compliance Guidelines](./security-guidelines.md)
- [API Documentation](./api-documentation.md)
- [Operation & Monitoring Procedures](./operations-procedures.md)
