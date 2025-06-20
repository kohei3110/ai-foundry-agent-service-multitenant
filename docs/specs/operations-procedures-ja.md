# Operations & Monitoring Procedures for Pooled Multi-Tenant Architecture

*Version 1.0 – 2025-06-20*

## 1. 概要

本書は、Azure AI Foundry Agent Service (FAS) のPooled（共有）マルチテナント方式における運用・監視手順を定義します。24/7稼働を前提とした自動化された監視、アラート、およびインシデント対応手順を包含します。

## 2. 運用体制

### 2.1 責任体制

| ロール | 責任範囲 | 勤務時間 | エスカレーション |
|--------|----------|----------|------------------|
| **L1 Support** | 基本監視、初期対応 | 24/7 | L2 Support |
| **L2 Support** | 技術調査、復旧作業 | 平日 9-18時 | L3 Support |
| **L3 Support** | 深層解析、開発対応 | オンコール | アーキテクト |
| **SRE Team** | インフラ運用、最適化 | 平日 9-18時 | インフラ責任者 |
| **Security Team** | セキュリティ監視、対応 | 24/7 | CISO |

### 2.2 オンコール体制

```mermaid
flowchart TD
    A[アラート発生] --> B{重要度判定}
    B -->|Critical| C[L3 即座エスカレーション]
    B -->|High| D[L2 1時間以内対応]
    B -->|Medium| E[L1 4時間以内対応]
    B -->|Low| F[L1 翌営業日対応]
    
    C --> G[アーキテクト通知]
    D --> H{解決可能?}
    H -->|Yes| I[対応・解決]
    H -->|No| J[L3エスカレーション]
    
    E --> K{調査・対応}
    K -->|解決| I
    K -->|エスカレーション| D
```

## 3. 監視戦略

### 3.1 監視レイヤー

#### 3.1.1 インフラストラクチャ監視
- **Azure Monitor**: リソース正常性、メトリクス
- **Network Watcher**: ネットワーク接続性
- **Azure Security Center**: セキュリティ状態

#### 3.1.2 アプリケーション監視
- **Application Insights**: パフォーマンス、可用性
- **Custom Metrics**: ビジネスメトリクス
- **Distributed Tracing**: リクエスト追跡

#### 3.1.3 ビジネス監視
- **テナント別 SLA**: 可用性、レスポンス時間
- **利用量メトリクス**: API呼び出し、データ使用量
- **コスト監視**: リソース使用コスト

### 3.2 SLA定義

| メトリクス | SLA目標 | 測定期間 | アラート閾値 |
|-----------|----------|----------|--------------|
| **可用性** | 99.9% | 月次 | < 99.95% |
| **レスポンス時間** | < 2秒 (95th) | 5分間 | > 3秒 |
| **エラー率** | < 0.1% | 5分間 | > 0.5% |
| **テナント分離** | 100% | リアルタイム | > 0% |

## 4. 監視ダッシュボード

### 4.1 運用ダッシュボード構成

#### 4.1.1 メインダッシュボード
```json
{
  "dashboard": {
    "name": "AI Foundry Agents - Operations Overview",
    "widgets": [
      {
        "type": "metric",
        "title": "Overall System Health",
        "query": "Heartbeat | summarize avg(TimeGenerated) by Computer",
        "visualization": "singlestat"
      },
      {
        "type": "metric", 
        "title": "Request Rate (per minute)",
        "query": "requests | summarize count() by bin(timestamp, 1m)",
        "visualization": "timechart"
      },
      {
        "type": "metric",
        "title": "Error Rate by Tenant",
        "query": "requests | where resultCode >= 400 | summarize ErrorRate = count() * 100.0 / prev(count()) by tostring(customDimensions.tenantId)",
        "visualization": "table"
      },
      {
        "type": "metric",
        "title": "Response Time Distribution",
        "query": "requests | summarize percentiles(duration, 50, 90, 95, 99)",
        "visualization": "barchart"
      }
    ]
  }
}
```

#### 4.1.2 テナント別ダッシュボード
```kql
// テナント別パフォーマンス監視
let TenantId = "contoso";
requests
| where customDimensions.tenantId == TenantId
| where timestamp > ago(1h)
| summarize 
    RequestCount = count(),
    AvgDuration = avg(duration),
    ErrorRate = countif(resultCode >= 400) * 100.0 / count(),
    P95Duration = percentile(duration, 95)
by bin(timestamp, 5m)
| render timechart

// テナント別リソース使用量
let TenantId = "contoso";
customMetrics
| where name in ("cosmos_ru_consumption", "search_query_count", "storage_transactions")
| where customDimensions.tenantId == TenantId
| where timestamp > ago(24h)
| summarize Value = avg(value) by name, bin(timestamp, 1h)
| render timechart

// テナント境界チェック
traces
| where customDimensions has "tenantId"
| where message contains "boundary" or message contains "unauthorized"
| summarize ViolationCount = count() by 
    TenantId = tostring(customDimensions.tenantId),
    bin(timestamp, 1h)
| render timechart
```

### 4.2 セキュリティダッシュボード

#### 4.2.1 セキュリティメトリクス
```kql
// 認証失敗監視
SecurityEvent
| where EventID == 4625
| where TimeGenerated > ago(1h)
| summarize FailedLogins = count() by 
    Account = tolower(Account),
    TenantId = tostring(customDimensions.tenantId),
    bin(TimeGenerated, 5m)
| where FailedLogins > 5
| render timechart

// 異常なAPIアクセスパターン
requests
| where timestamp > ago(1h)
| summarize 
    RequestCount = count(),
    UniqueIPs = dcount(client_IP)
by 
    UserId = tostring(customDimensions.userId),
    TenantId = tostring(customDimensions.tenantId),
    bin(timestamp, 5m)
| where RequestCount > 100 or UniqueIPs > 10
| order by RequestCount desc

// データアクセス監査
AppTraces
| where Message contains "dataAccess"
| where TimeGenerated > ago(24h)
| extend 
    Operation = tostring(customDimensions.operation),
    DataClassification = tostring(customDimensions.dataClassification),
    TenantId = tostring(customDimensions.tenantId)
| summarize AccessCount = count() by Operation, DataClassification, TenantId
| render piechart
```

## 5. アラート設定

### 5.1 Critical アラート

#### 5.1.1 システム可用性
```json
{
  "alertRule": {
    "name": "SystemAvailabilityDrop",
    "description": "System availability below 99.95%",
    "severity": "Critical",
    "enabled": true,
    "query": "requests | where timestamp > ago(5m) | summarize SuccessRate = countif(resultCode < 400) * 100.0 / count()",
    "threshold": 99.95,
    "operator": "LessThan",
    "timeWindow": "PT5M",
    "evaluationFrequency": "PT1M",
    "actionGroups": [
      "oncall-critical",
      "sre-team",
      "management"
    ],
    "autoMitigation": false
  }
}
```

#### 5.1.2 テナント境界違反
```json
{
  "alertRule": {
    "name": "TenantBoundaryViolation",
    "description": "Tenant boundary violation detected",
    "severity": "Critical",
    "enabled": true,
    "query": "traces | where message contains 'boundary violation' or message contains 'unauthorized tenant access'",
    "threshold": 1,
    "operator": "GreaterThan",
    "timeWindow": "PT1M",
    "evaluationFrequency": "PT1M",
    "actionGroups": [
      "security-team",
      "oncall-critical"
    ],
    "autoMitigation": false
  }
}
```

#### 5.1.3 高エラー率
```json
{
  "alertRule": {
    "name": "HighErrorRate",
    "description": "Error rate exceeds 5% for any tenant",
    "severity": "High",
    "enabled": true,
    "query": "requests | where timestamp > ago(5m) | summarize ErrorRate = countif(resultCode >= 400) * 100.0 / count() by tostring(customDimensions.tenantId) | where ErrorRate > 5",
    "threshold": 1,
    "operator": "GreaterThan",
    "timeWindow": "PT5M",
    "evaluationFrequency": "PT1M",
    "actionGroups": [
      "oncall-high",
      "tenant-admin"
    ],
    "autoMitigation": false
  }
}
```

### 5.2 Performance アラート

#### 5.2.1 レスポンス時間劣化
```kql
// P95レスポンス時間監視
requests
| where timestamp > ago(5m)
| summarize P95Duration = percentile(duration, 95) by tostring(customDimensions.tenantId)
| where P95Duration > 3000  // 3秒
```

#### 5.2.2 リソース使用量
```kql
// Cosmos DB RU消費量監視
customMetrics
| where name == "cosmos_ru_consumption"
| where timestamp > ago(5m)
| summarize AvgRU = avg(value) by tostring(customDimensions.tenantId)
| where AvgRU > 8000  // 80%使用量
```

## 6. 自動修復機能

### 6.1 Auto-scaling

#### 6.1.1 Cosmos DB Auto-scale
```python
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
import logging

class CosmosAutoScaler:
    """Cosmos DB 自動スケーリング"""
    
    def __init__(self, account_url: str, database_name: str):
        credential = DefaultAzureCredential()
        self.client = CosmosClient(account_url, credential)
        self.database = self.client.get_database_client(database_name)
        self.logger = logging.getLogger(__name__)
    
    def monitor_and_scale(self):
        """RU消費量監視と自動スケーリング"""
        containers = ["threads", "messages", "runs", "files"]
        
        for container_name in containers:
            container = self.database.get_container_client(container_name)
            
            # 現在のスループット取得
            offer = container.read_offer()
            current_throughput = offer['content']['offerThroughput']
            
            # 使用率確認（過去5分間）
            usage_percent = self.get_ru_usage_percent(container_name)
            
            if usage_percent > 80:
                # スケールアップ
                new_throughput = min(current_throughput * 2, 20000)
                container.replace_throughput(new_throughput)
                self.logger.info(f"Scaled up {container_name} from {current_throughput} to {new_throughput} RU/s")
                
            elif usage_percent < 20 and current_throughput > 400:
                # スケールダウン
                new_throughput = max(current_throughput // 2, 400)
                container.replace_throughput(new_throughput)
                self.logger.info(f"Scaled down {container_name} from {current_throughput} to {new_throughput} RU/s")
    
    def get_ru_usage_percent(self, container_name: str) -> float:
        """RU使用率取得"""
        # Application Insights からメトリクス取得
        # 実際の実装では Application Insights API を使用
        return 50.0  # プレースホルダー
```

#### 6.1.2 Container Apps Auto-scale
```yaml
# Container Apps auto-scaling configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-foundry-agent-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-foundry-agent-service
  template:
    spec:
      containers:
      - name: agent-service
        image: your-registry/agent-service:latest
        resources:
          requests:
            cpu: "0.25"
            memory: "0.5Gi"
          limits:
            cpu: "1.0"
            memory: "2.0Gi"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-foundry-agent-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 6.2 自動復旧スクリプト

#### 6.2.1 ヘルスチェック・復旧
```python
import asyncio
import aiohttp
import logging
from typing import Dict, List
from datetime import datetime, timedelta

class HealthCheckMonitor:
    """ヘルスチェック・自動復旧"""
    
    def __init__(self, endpoints: List[Dict[str, str]]):
        self.endpoints = endpoints
        self.logger = logging.getLogger(__name__)
        self.failed_checks = {}
    
    async def check_endpoint_health(self, endpoint: Dict[str, str]) -> bool:
        """エンドポイントヘルスチェック"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint['url'] + '/health',
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Health check failed for {endpoint['name']}: {e}")
            return False
    
    async def monitor_health(self):
        """継続的ヘルスチェック"""
        while True:
            for endpoint in self.endpoints:
                is_healthy = await self.check_endpoint_health(endpoint)
                
                if not is_healthy:
                    await self.handle_unhealthy_endpoint(endpoint)
                else:
                    # 復旧した場合
                    if endpoint['name'] in self.failed_checks:
                        self.logger.info(f"Endpoint {endpoint['name']} recovered")
                        del self.failed_checks[endpoint['name']]
            
            await asyncio.sleep(60)  # 1分間隔
    
    async def handle_unhealthy_endpoint(self, endpoint: Dict[str, str]):
        """不正常エンドポイント処理"""
        endpoint_name = endpoint['name']
        
        # 失敗回数カウント
        if endpoint_name not in self.failed_checks:
            self.failed_checks[endpoint_name] = {
                'count': 1,
                'first_failure': datetime.utcnow()
            }
        else:
            self.failed_checks[endpoint_name]['count'] += 1
        
        failure_info = self.failed_checks[endpoint_name]
        
        # 3回連続失敗で自動復旧試行
        if failure_info['count'] >= 3:
            await self.attempt_auto_recovery(endpoint)
        
        # 10分間継続失敗でエスカレーション
        if datetime.utcnow() - failure_info['first_failure'] > timedelta(minutes=10):
            await self.escalate_incident(endpoint, failure_info)
    
    async def attempt_auto_recovery(self, endpoint: Dict[str, str]):
        """自動復旧試行"""
        self.logger.info(f"Attempting auto-recovery for {endpoint['name']}")
        
        recovery_actions = [
            self.restart_service,
            self.clear_cache,
            self.scale_up_resources
        ]
        
        for action in recovery_actions:
            try:
                success = await action(endpoint)
                if success:
                    self.logger.info(f"Auto-recovery successful for {endpoint['name']}")
                    return
            except Exception as e:
                self.logger.error(f"Recovery action failed: {e}")
        
        self.logger.error(f"All auto-recovery attempts failed for {endpoint['name']}")
    
    async def restart_service(self, endpoint: Dict[str, str]) -> bool:
        """サービス再起動"""
        # Container Apps の再起動実装
        # Azure REST API または Azure CLI を使用
        return False  # プレースホルダー
    
    async def clear_cache(self, endpoint: Dict[str, str]) -> bool:
        """キャッシュクリア"""
        # Redis または Application Cache のクリア
        return False  # プレースホルダー
    
    async def scale_up_resources(self, endpoint: Dict[str, str]) -> bool:
        """リソーススケールアップ"""
        # Container Apps のスケールアップ
        return False  # プレースホルダー
    
    async def escalate_incident(self, endpoint: Dict[str, str], failure_info: Dict):
        """インシデントエスカレーション"""
        incident_data = {
            "title": f"Service {endpoint['name']} Unavailable",
            "description": f"Service has been unhealthy for {failure_info['count']} checks",
            "severity": "High",
            "endpoint": endpoint,
            "failure_duration": datetime.utcnow() - failure_info['first_failure']
        }
        
        # インシデント管理システムに通知
        await self.create_incident(incident_data)
    
    async def create_incident(self, incident_data: Dict):
        """インシデント作成"""
        # ServiceNow、JIRA、または Azure DevOps にインシデント作成
        self.logger.critical(f"Incident created: {incident_data}")
```

## 7. 容量計画

### 7.1 リソース使用量予測

#### 7.1.1 予測モデル
```python
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
import numpy as np
from datetime import datetime, timedelta

class CapacityPlanner:
    """容量計画・予測"""
    
    def __init__(self):
        self.models = {}
        self.historical_data = {}
    
    def collect_historical_metrics(self, days: int = 30) -> Dict[str, pd.DataFrame]:
        """過去メトリクス収集"""
        # Application Insights からメトリクス取得
        metrics = {
            'requests_per_minute': self.get_requests_metrics(days),
            'cosmos_ru_consumption': self.get_cosmos_metrics(days),
            'memory_usage': self.get_memory_metrics(days),
            'cpu_usage': self.get_cpu_metrics(days)
        }
        return metrics
    
    def train_prediction_models(self):
        """予測モデル訓練"""
        historical_data = self.collect_historical_metrics()
        
        for metric_name, data in historical_data.items():
            if len(data) < 7:  # 最低7日分のデータが必要
                continue
            
            # 特徴量作成
            data['hour'] = data.index.hour
            data['day_of_week'] = data.index.dayofweek
            data['day_of_month'] = data.index.day
            
            X = data[['hour', 'day_of_week', 'day_of_month']].values
            y = data['value'].values
            
            # 線形回帰モデル訓練
            model = LinearRegression()
            model.fit(X, y)
            
            self.models[metric_name] = model
            self.historical_data[metric_name] = data
    
    def predict_capacity_needs(self, days_ahead: int = 7) -> Dict[str, Dict]:
        """容量予測"""
        predictions = {}
        
        for metric_name, model in self.models.items():
            future_dates = pd.date_range(
                start=datetime.now(),
                periods=days_ahead * 24,  # 時間単位
                freq='H'
            )
            
            # 特徴量作成
            future_features = np.array([
                [date.hour, date.dayofweek, date.day] 
                for date in future_dates
            ])
            
            # 予測実行
            predicted_values = model.predict(future_features)
            
            predictions[metric_name] = {
                'dates': future_dates,
                'values': predicted_values,
                'max_predicted': np.max(predicted_values),
                'avg_predicted': np.mean(predicted_values)
            }
        
        return predictions
    
    def generate_capacity_recommendations(self) -> List[Dict]:
        """容量推奨事項生成"""
        predictions = self.predict_capacity_needs()
        recommendations = []
        
        # Cosmos DB RU推奨
        if 'cosmos_ru_consumption' in predictions:
            max_ru = predictions['cosmos_ru_consumption']['max_predicted']
            current_ru = self.get_current_cosmos_throughput()
            
            if max_ru > current_ru * 0.8:  # 80%使用率超過予測
                recommended_ru = int(max_ru * 1.2)  # 20%バッファ
                recommendations.append({
                    'service': 'Cosmos DB',
                    'current_capacity': current_ru,
                    'recommended_capacity': recommended_ru,
                    'reason': f'Predicted peak usage: {max_ru:.0f} RU/s',
                    'urgency': 'High' if max_ru > current_ru else 'Medium'
                })
        
        # Container Apps スケール推奨
        if 'requests_per_minute' in predictions:
            max_rpm = predictions['requests_per_minute']['max_predicted']
            current_instances = self.get_current_container_instances()
            
            # 1インスタンスあたり100RPM処理可能と仮定
            required_instances = int(max_rpm / 100) + 1
            
            if required_instances > current_instances:
                recommendations.append({
                    'service': 'Container Apps',
                    'current_capacity': current_instances,
                    'recommended_capacity': required_instances,
                    'reason': f'Predicted peak: {max_rpm:.0f} RPM',
                    'urgency': 'Medium'
                })
        
        return recommendations
    
    def get_requests_metrics(self, days: int) -> pd.DataFrame:
        """リクエストメトリクス取得"""
        # プレースホルダー実装
        return pd.DataFrame()
    
    def get_cosmos_metrics(self, days: int) -> pd.DataFrame:
        """Cosmos DBメトリクス取得"""
        # プレースホルダー実装
        return pd.DataFrame()
    
    def get_memory_metrics(self, days: int) -> pd.DataFrame:
        """メモリメトリクス取得"""
        # プレースホルダー実装
        return pd.DataFrame()
    
    def get_cpu_metrics(self, days: int) -> pd.DataFrame:
        """CPUメトリクス取得"""
        # プレースホルダー実装
        return pd.DataFrame()
    
    def get_current_cosmos_throughput(self) -> int:
        """現在のCosmos DBスループット取得"""
        # プレースホルダー実装
        return 1000
    
    def get_current_container_instances(self) -> int:
        """現在のContainer Appsインスタンス数取得"""
        # プレースホルダー実装
        return 2
```

### 7.2 コスト最適化

#### 7.2.1 コスト監視・アラート
```kql
// 日次コスト監視
Usage
| where TimeGenerated > ago(1d)
| where MeterId has "cosmos" or MeterId has "search" or MeterId has "storage"
| summarize TotalCost = sum(Quantity * UnitPrice) by 
    ServiceName = tostring(MeterCategory),
    TenantId = tostring(Tags.tenantId)
| order by TotalCost desc

// 予算超過アラート
Usage
| where TimeGenerated > startofmonth(now())
| summarize MonthlySpend = sum(Quantity * UnitPrice) by TenantId = tostring(Tags.tenantId)
| join kind=inner (
    BudgetData
    | project TenantId, MonthlyBudget
) on TenantId
| where MonthlySpend > MonthlyBudget * 0.8  // 80%使用でアラート
| project TenantId, MonthlySpend, MonthlyBudget, UsagePercent = MonthlySpend / MonthlyBudget * 100
```

#### 7.2.2 自動最適化スクリプト
```python
class CostOptimizer:
    """コスト最適化"""
    
    def __init__(self):
        self.recommendations = []
    
    def analyze_cosmos_usage(self) -> List[Dict]:
        """Cosmos DB使用量分析"""
        recommendations = []
        
        # 低使用率コンテナ検出
        low_usage_containers = self.find_low_usage_containers()
        
        for container in low_usage_containers:
            if container['usage_percent'] < 20:
                current_ru = container['provisioned_ru']
                recommended_ru = max(400, int(current_ru * 0.5))
                
                recommendations.append({
                    'service': 'Cosmos DB',
                    'container': container['name'],
                    'current_ru': current_ru,
                    'recommended_ru': recommended_ru,
                    'potential_savings': self.calculate_cosmos_savings(current_ru, recommended_ru),
                    'action': 'scale_down'
                })
        
        return recommendations
    
    def analyze_storage_usage(self) -> List[Dict]:
        """Storage使用量分析"""
        recommendations = []
        
        # アクセス頻度の低いデータをクールティアに移動
        old_data = self.find_old_unused_data()
        
        for data in old_data:
            if data['last_access'] > 30:  # 30日間未アクセス
                recommendations.append({
                    'service': 'Blob Storage',
                    'container': data['container'],
                    'size_gb': data['size_gb'],
                    'current_tier': 'Hot',
                    'recommended_tier': 'Cool',
                    'potential_savings': data['size_gb'] * 0.01,  # $0.01/GB差額
                    'action': 'change_tier'
                })
        
        return recommendations
    
    def implement_optimization(self, recommendation: Dict):
        """最適化実装"""
        if recommendation['service'] == 'Cosmos DB' and recommendation['action'] == 'scale_down':
            self.scale_cosmos_container(
                recommendation['container'],
                recommendation['recommended_ru']
            )
        elif recommendation['service'] == 'Blob Storage' and recommendation['action'] == 'change_tier':
            self.change_blob_tier(
                recommendation['container'],
                recommendation['recommended_tier']
            )
    
    def find_low_usage_containers(self) -> List[Dict]:
        """低使用率コンテナ検出"""
        # プレースホルダー実装
        return []
    
    def find_old_unused_data(self) -> List[Dict]:
        """古い未使用データ検出"""
        # プレースホルダー実装
        return []
    
    def calculate_cosmos_savings(self, current_ru: int, new_ru: int) -> float:
        """Cosmos DB節約額計算"""
        hourly_cost_per_100ru = 0.008  # $/hour
        hourly_savings = (current_ru - new_ru) / 100 * hourly_cost_per_100ru
        return hourly_savings * 24 * 30  # 月次節約額
    
    def scale_cosmos_container(self, container_name: str, new_ru: int):
        """Cosmos DBコンテナスケール"""
        # プレースホルダー実装
        pass
    
    def change_blob_tier(self, container_name: str, new_tier: str):
        """Blobティア変更"""
        # プレースホルダー実装
        pass
```

## 8. バックアップ・災害復旧

### 8.1 バックアップ戦略

#### 8.1.1 データバックアップ
| サービス | バックアップ頻度 | 保持期間 | 復旧目標時間 (RTO) |
|---------|------------------|----------|-------------------|
| **Cosmos DB** | 継続的 | 30日 | < 4時間 |
| **AI Search** | 日次 | 30日 | < 8時間 |
| **Blob Storage** | リアルタイム (GRS) | 無制限 | < 2時間 |
| **Key Vault** | 自動 | 90日 | < 1時間 |

#### 8.1.2 設定バックアップ
```bash
#!/bin/bash
# Infrastructure as Code バックアップ

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/${BACKUP_DATE}"

# Bicep テンプレートバックアップ
mkdir -p ${BACKUP_DIR}/infrastructure
cp -r ./infra/* ${BACKUP_DIR}/infrastructure/

# 設定ファイルバックアップ
mkdir -p ${BACKUP_DIR}/config
cp -r ./config/* ${BACKUP_DIR}/config/

# Azure リソース設定エクスポート
az group export --name rg-fas-pooled-prod --output-format json > ${BACKUP_DIR}/resource-group-config.json

# Key Vault シークレット一覧エクスポート (値は除く)
az keyvault secret list --vault-name kv-contoso-prod --query "[].{name:name,enabled:attributes.enabled}" > ${BACKUP_DIR}/keyvault-secrets-list.json

# Git リポジトリにコミット
git add ${BACKUP_DIR}
git commit -m "Automated backup - ${BACKUP_DATE}"
git push origin backup-branch

echo "Backup completed: ${BACKUP_DIR}"
```

### 8.2 災害復旧手順

#### 8.2.1 DR実行手順
```python
import asyncio
import logging
from typing import Dict, List
from datetime import datetime

class DisasterRecoveryManager:
    """災害復旧管理"""
    
    def __init__(self, dr_config: Dict):
        self.dr_config = dr_config
        self.logger = logging.getLogger(__name__)
        self.recovery_steps = []
    
    async def execute_disaster_recovery(self, disaster_type: str):
        """災害復旧実行"""
        self.logger.critical(f"Initiating disaster recovery for: {disaster_type}")
        
        recovery_plan = self.get_recovery_plan(disaster_type)
        
        for step in recovery_plan['steps']:
            try:
                await self.execute_recovery_step(step)
                self.recovery_steps.append({
                    'step': step['name'],
                    'status': 'completed',
                    'timestamp': datetime.utcnow()
                })
            except Exception as e:
                self.logger.error(f"Recovery step failed: {step['name']} - {e}")
                self.recovery_steps.append({
                    'step': step['name'],
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.utcnow()
                })
                
                if step.get('critical', False):
                    raise Exception(f"Critical recovery step failed: {step['name']}")
    
    def get_recovery_plan(self, disaster_type: str) -> Dict:
        """復旧計画取得"""
        plans = {
            'region_outage': {
                'steps': [
                    {'name': 'validate_dr_region', 'function': 'validate_dr_region', 'critical': True},
                    {'name': 'failover_cosmos_db', 'function': 'failover_cosmos_db', 'critical': True},
                    {'name': 'restore_ai_search', 'function': 'restore_ai_search', 'critical': True},
                    {'name': 'deploy_container_apps', 'function': 'deploy_container_apps', 'critical': True},
                    {'name': 'update_dns_records', 'function': 'update_dns_records', 'critical': True},
                    {'name': 'validate_services', 'function': 'validate_services', 'critical': True},
                    {'name': 'notify_stakeholders', 'function': 'notify_stakeholders', 'critical': False}
                ]
            },
            'data_corruption': {
                'steps': [
                    {'name': 'isolate_corrupted_data', 'function': 'isolate_corrupted_data', 'critical': True},
                    {'name': 'restore_from_backup', 'function': 'restore_from_backup', 'critical': True},
                    {'name': 'validate_data_integrity', 'function': 'validate_data_integrity', 'critical': True},
                    {'name': 'resume_operations', 'function': 'resume_operations', 'critical': True}
                ]
            },
            'security_breach': {
                'steps': [
                    {'name': 'isolate_affected_systems', 'function': 'isolate_affected_systems', 'critical': True},
                    {'name': 'revoke_compromised_credentials', 'function': 'revoke_credentials', 'critical': True},
                    {'name': 'deploy_patched_systems', 'function': 'deploy_patched_systems', 'critical': True},
                    {'name': 'restore_from_clean_backup', 'function': 'restore_clean_backup', 'critical': True},
                    {'name': 'security_validation', 'function': 'security_validation', 'critical': True}
                ]
            }
        }
        
        return plans.get(disaster_type, {'steps': []})
    
    async def execute_recovery_step(self, step: Dict):
        """復旧ステップ実行"""
        function_name = step['function']
        
        if hasattr(self, function_name):
            function = getattr(self, function_name)
            await function()
        else:
            raise Exception(f"Recovery function not found: {function_name}")
    
    async def validate_dr_region(self):
        """DR リージョン検証"""
        # DR リージョンの可用性確認
        pass
    
    async def failover_cosmos_db(self):
        """Cosmos DB フェイルオーバー"""
        # Cosmos DB の手動フェイルオーバー実行
        pass
    
    async def restore_ai_search(self):
        """AI Search 復元"""
        # インデックス再構築
        pass
    
    async def deploy_container_apps(self):
        """Container Apps デプロイ"""
        # DR リージョンにアプリケーションデプロイ
        pass
    
    async def update_dns_records(self):
        """DNS レコード更新"""
        # Traffic Manager または DNS の更新
        pass
    
    async def validate_services(self):
        """サービス検証"""
        # 全サービスのヘルスチェック実行
        pass
    
    async def notify_stakeholders(self):
        """ステークホルダー通知"""
        # 復旧完了通知
        pass
```

## 9. 運用自動化

### 9.1 定期メンテナンス

#### 9.1.1 自動メンテナンススクリプト
```python
import schedule
import time
import logging
from datetime import datetime

class MaintenanceAutomation:
    """定期メンテナンス自動化"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def setup_maintenance_schedule(self):
        """メンテナンススケジュール設定"""
        
        # 日次メンテナンス (深夜2時)
        schedule.every().day.at("02:00").do(self.daily_maintenance)
        
        # 週次メンテナンス (日曜日深夜3時)
        schedule.every().sunday.at("03:00").do(self.weekly_maintenance)
        
        # 月次メンテナンス (毎月1日深夜4時)
        schedule.every().month.do(self.monthly_maintenance)
    
    def daily_maintenance(self):
        """日次メンテナンス"""
        self.logger.info("Starting daily maintenance")
        
        tasks = [
            self.cleanup_old_logs,
            self.optimize_cosmos_indexing,
            self.validate_backup_integrity,
            self.update_security_patches,
            self.check_certificate_expiry
        ]
        
        for task in tasks:
            try:
                task()
                self.logger.info(f"Completed: {task.__name__}")
            except Exception as e:
                self.logger.error(f"Failed: {task.__name__} - {e}")
    
    def weekly_maintenance(self):
        """週次メンテナンス"""
        self.logger.info("Starting weekly maintenance")
        
        tasks = [
            self.analyze_performance_trends,
            self.update_capacity_recommendations,
            self.security_vulnerability_scan,
            self.backup_configuration_files
        ]
        
        for task in tasks:
            try:
                task()
                self.logger.info(f"Completed: {task.__name__}")
            except Exception as e:
                self.logger.error(f"Failed: {task.__name__} - {e}")
    
    def monthly_maintenance(self):
        """月次メンテナンス"""
        self.logger.info("Starting monthly maintenance")
        
        tasks = [
            self.generate_monthly_report,
            self.review_cost_optimization,
            self.update_disaster_recovery_plan,
            self.conduct_security_audit
        ]
        
        for task in tasks:
            try:
                task()
                self.logger.info(f"Completed: {task.__name__}")
            except Exception as e:
                self.logger.error(f"Failed: {task.__name__} - {e}")
    
    def cleanup_old_logs(self):
        """古いログクリーンアップ"""
        # 30日以上古いログを削除
        pass
    
    def optimize_cosmos_indexing(self):
        """Cosmos DB インデックス最適化"""
        # 使用されていないインデックスを検出・削除
        pass
    
    def validate_backup_integrity(self):
        """バックアップ整合性検証"""
        # バックアップからのテスト復元実行
        pass
    
    def update_security_patches(self):
        """セキュリティパッチ更新"""
        # Container Images の最新パッチ適用
        pass
    
    def check_certificate_expiry(self):
        """証明書有効期限チェック"""
        # SSL証明書の有効期限確認
        pass
    
    def analyze_performance_trends(self):
        """パフォーマンストレンド分析"""
        # 週次パフォーマンスレポート生成
        pass
    
    def update_capacity_recommendations(self):
        """容量推奨事項更新"""
        # 容量計画の更新
        pass
    
    def security_vulnerability_scan(self):
        """セキュリティ脆弱性スキャン"""
        # 自動脆弱性スキャン実行
        pass
    
    def backup_configuration_files(self):
        """設定ファイルバックアップ"""
        # インフラ設定のバックアップ
        pass
    
    def generate_monthly_report(self):
        """月次レポート生成"""
        # SLA達成状況、コスト、セキュリティレポート生成
        pass
    
    def review_cost_optimization(self):
        """コスト最適化レビュー"""
        # 月次コスト分析・最適化提案
        pass
    
    def update_disaster_recovery_plan(self):
        """災害復旧計画更新"""
        # DR計画の定期見直し
        pass
    
    def conduct_security_audit(self):
        """セキュリティ監査実施"""
        # 月次セキュリティ監査
        pass
    
    def run_scheduler(self):
        """スケジューラー実行"""
        self.logger.info("Maintenance scheduler started")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分間隔でチェック
```

### 9.2 CI/CD パイプライン

#### 9.2.1 デプロイメントパイプライン
```yaml
# Azure DevOps Pipeline
trigger:
  branches:
    include:
    - main
    - develop

variables:
  azureSubscription: 'Azure-Subscription'
  resourceGroupName: 'rg-fas-pooled-$(environment)'
  containerRegistry: 'acr-fas-pooled.azurecr.io'

stages:
- stage: Build
  jobs:
  - job: BuildApplication
    steps:
    - task: Docker@2
      displayName: 'Build and Push Docker Image'
      inputs:
        containerRegistry: $(containerRegistry)
        repository: 'ai-foundry-agent-service'
        command: 'buildAndPush'
        Dockerfile: 'Dockerfile'
        tags: |
          $(Build.BuildId)
          latest

    - task: AzureCLI@2
      displayName: 'Security Scan'
      inputs:
        azureSubscription: $(azureSubscription)
        scriptType: 'bash'
        scriptLocation: 'inlineScript'
        inlineScript: |
          # Container security scan
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy image $(containerRegistry)/ai-foundry-agent-service:$(Build.BuildId)

- stage: Test
  dependsOn: Build
  jobs:
  - job: SecurityTests
    steps:
    - task: PythonScript@0
      displayName: 'Run Security Tests'
      inputs:
        scriptSource: 'filePath'
        scriptPath: 'tests/security/run_security_tests.py'

  - job: IntegrationTests
    steps:
    - task: PythonScript@0
      displayName: 'Run Integration Tests'
      inputs:
        scriptSource: 'filePath'
        scriptPath: 'tests/integration/run_integration_tests.py'

- stage: Deploy
  dependsOn: Test
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - deployment: DeployToProduction
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: AzureResourceManagerTemplateDeployment@3
            displayName: 'Deploy Infrastructure'
            inputs:
              deploymentScope: 'Resource Group'
              azureResourceManagerConnection: $(azureSubscription)
              subscriptionId: $(subscriptionId)
              action: 'Create Or Update Resource Group'
              resourceGroupName: $(resourceGroupName)
              location: 'Japan East'
              templateLocation: 'Linked artifact'
              csmFile: 'infra/main.bicep'
              csmParametersFile: 'infra/main.parameters.prod.json'

          - task: AzureContainerApps@1
            displayName: 'Deploy Application'
            inputs:
              azureSubscription: $(azureSubscription)
              containerAppName: 'ca-ai-foundry-agent-service'
              resourceGroup: $(resourceGroupName)
              imageToDeploy: '$(containerRegistry)/ai-foundry-agent-service:$(Build.BuildId)'

          - task: AzureCLI@2
            displayName: 'Post-Deployment Validation'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                # Health check
                curl -f https://api-prod.example.com/health || exit 1
                
                # Smoke tests
                python tests/smoke/smoke_tests.py
```

## 10. レポーティング

### 10.1 SLA レポート

#### 10.1.1 月次SLAレポート
```kql
// 月次SLAレポート生成
let StartTime = startofmonth(now());
let EndTime = now();

let AvailabilityData = requests
| where timestamp between (StartTime .. EndTime)
| summarize 
    TotalRequests = count(),
    SuccessfulRequests = countif(resultCode < 400),
    FailedRequests = countif(resultCode >= 400)
by TenantId = tostring(customDimensions.tenantId)
| extend AvailabilityPercent = round(SuccessfulRequests * 100.0 / TotalRequests, 3);

let PerformanceData = requests
| where timestamp between (StartTime .. EndTime)
| where resultCode < 400
| summarize 
    AvgResponseTime = avg(duration),
    P95ResponseTime = percentile(duration, 95),
    P99ResponseTime = percentile(duration, 99)
by TenantId = tostring(customDimensions.tenantId);

AvailabilityData
| join kind=inner PerformanceData on TenantId
| project 
    TenantId,
    AvailabilityPercent,
    SLAMet = iff(AvailabilityPercent >= 99.9, "✓", "✗"),
    AvgResponseTime = round(AvgResponseTime, 2),
    P95ResponseTime = round(P95ResponseTime, 2),
    P99ResponseTime = round(P99ResponseTime, 2),
    TotalRequests,
    FailedRequests
| order by TenantId asc
```

### 10.2 運用レポート自動生成

#### 10.2.1 レポート生成スクリプト
```python
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

class OperationalReportGenerator:
    """運用レポート自動生成"""
    
    def __init__(self, app_insights_client):
        self.ai_client = app_insights_client
    
    def generate_monthly_report(self, year: int, month: int):
        """月次運用レポート生成"""
        start_date = datetime(year, month, 1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        report_data = {
            'period': f"{year}-{month:02d}",
            'sla_metrics': self.get_sla_metrics(start_date, end_date),
            'performance_metrics': self.get_performance_metrics(start_date, end_date),
            'security_metrics': self.get_security_metrics(start_date, end_date),
            'cost_metrics': self.get_cost_metrics(start_date, end_date),
            'incidents': self.get_incidents(start_date, end_date)
        }
        
        # HTML レポート生成
        html_report = self.generate_html_report(report_data)
        
        # PDF レポート生成
        pdf_report = self.generate_pdf_report(report_data)
        
        # ステークホルダーに送信
        self.send_report_email(html_report, pdf_report, report_data['period'])
        
        return report_data
    
    def get_sla_metrics(self, start_date: datetime, end_date: datetime) -> dict:
        """SLA メトリクス取得"""
        # KQL クエリでSLAデータ取得
        query = f"""
        requests
        | where timestamp between (datetime({start_date.isoformat()}) .. datetime({end_date.isoformat()}))
        | summarize 
            TotalRequests = count(),
            SuccessfulRequests = countif(resultCode < 400),
            AvgDuration = avg(duration),
            P95Duration = percentile(duration, 95)
        by TenantId = tostring(customDimensions.tenantId)
        | extend AvailabilityPercent = round(SuccessfulRequests * 100.0 / TotalRequests, 3)
        """
        
        # プレースホルダー実装
        return {
            'overall_availability': 99.95,
            'tenant_availability': {
                'contoso': 99.97,
                'fabrikam': 99.93
            },
            'sla_breaches': 0
        }
    
    def get_performance_metrics(self, start_date: datetime, end_date: datetime) -> dict:
        """パフォーマンスメトリクス取得"""
        return {
            'avg_response_time': 1.2,
            'p95_response_time': 2.8,
            'p99_response_time': 5.1,
            'throughput_rpm': 1250
        }
    
    def get_security_metrics(self, start_date: datetime, end_date: datetime) -> dict:
        """セキュリティメトリクス取得"""
        return {
            'failed_authentications': 127,
            'tenant_boundary_violations': 0,
            'security_alerts': 3,
            'vulnerability_scans': 30
        }
    
    def get_cost_metrics(self, start_date: datetime, end_date: datetime) -> dict:
        """コストメトリクス取得"""
        return {
            'total_cost': 2850.30,
            'cost_per_tenant': {
                'contoso': 1420.15,
                'fabrikam': 1430.15
            },
            'cost_optimization_savings': 385.50
        }
    
    def get_incidents(self, start_date: datetime, end_date: datetime) -> list:
        """インシデント情報取得"""
        return [
            {
                'id': 'INC-2024-001',
                'title': 'Cosmos DB High Latency',
                'severity': 'Medium',
                'duration_minutes': 45,
                'affected_tenants': ['contoso']
            }
        ]
    
    def generate_html_report(self, report_data: dict) -> str:
        """HTML レポート生成"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Foundry Agents - Monthly Operations Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background-color: #0078d4; color: white; padding: 20px; }
                .section { margin: 20px 0; }
                .metric { display: inline-block; margin: 10px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
                .sla-met { color: green; font-weight: bold; }
                .sla-missed { color: red; font-weight: bold; }
                table { width: 100%; border-collapse: collapse; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AI Foundry Agents - Monthly Operations Report</h1>
                <p>Report Period: {period}</p>
            </div>
            
            <div class="section">
                <h2>SLA Summary</h2>
                <div class="metric">
                    <h3>Overall Availability</h3>
                    <p class="sla-met">{overall_availability}%</p>
                </div>
                <div class="metric">
                    <h3>SLA Breaches</h3>
                    <p>{sla_breaches}</p>
                </div>
            </div>
            
            <div class="section">
                <h2>Performance Metrics</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Target</th>
                        <th>Status</th>
                    </tr>
                    <tr>
                        <td>Average Response Time</td>
                        <td>{avg_response_time}s</td>
                        <td>&lt; 2s</td>
                        <td class="sla-met">✓</td>
                    </tr>
                    <tr>
                        <td>95th Percentile Response Time</td>
                        <td>{p95_response_time}s</td>
                        <td>&lt; 3s</td>
                        <td class="sla-met">✓</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Security Summary</h2>
                <p>Failed Authentications: {failed_authentications}</p>
                <p>Tenant Boundary Violations: {tenant_boundary_violations}</p>
                <p>Security Alerts: {security_alerts}</p>
            </div>
            
            <div class="section">
                <h2>Cost Summary</h2>
                <p>Total Monthly Cost: ${total_cost}</p>
                <p>Cost Optimization Savings: ${cost_optimization_savings}</p>
            </div>
        </body>
        </html>
        """.format(
            period=report_data['period'],
            overall_availability=report_data['sla_metrics']['overall_availability'],
            sla_breaches=report_data['sla_metrics']['sla_breaches'],
            avg_response_time=report_data['performance_metrics']['avg_response_time'],
            p95_response_time=report_data['performance_metrics']['p95_response_time'],
            failed_authentications=report_data['security_metrics']['failed_authentications'],
            tenant_boundary_violations=report_data['security_metrics']['tenant_boundary_violations'],
            security_alerts=report_data['security_metrics']['security_alerts'],
            total_cost=report_data['cost_metrics']['total_cost'],
            cost_optimization_savings=report_data['cost_metrics']['cost_optimization_savings']
        )
        
        return html_template
    
    def generate_pdf_report(self, report_data: dict) -> bytes:
        """PDF レポート生成"""
        # PDF生成実装 (weasyprint 等を使用)
        return b"PDF content placeholder"
    
    def send_report_email(self, html_report: str, pdf_report: bytes, period: str):
        """レポートメール送信"""
        recipients = [
            'operations@example.com',
            'management@example.com',
            'sre-team@example.com'
        ]
        
        msg = MIMEMultipart()
        msg['From'] = 'ai-foundry-ops@example.com'
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f'AI Foundry Agents - Monthly Operations Report ({period})'
        
        # HTML body
        msg.attach(MIMEText(html_report, 'html'))
        
        # PDF attachment
        pdf_attachment = MIMEImage(pdf_report)
        pdf_attachment.add_header('Content-Disposition', f'attachment; filename="operations-report-{period}.pdf"')
        msg.attach(pdf_attachment)
        
        # メール送信 (実際の実装では SMTP 設定が必要)
        # smtp_server = smtplib.SMTP('smtp.example.com', 587)
        # smtp_server.send_message(msg)
```

## 11. 関連ドキュメント

- [Pooled Infrastructure Specification](./pooled-infrastructure-spec.md)
- [Pooled Application Specification](./pooled-application-spec.md)
- [Security & Compliance Guidelines](./security-guidelines.md)
- [Incident Response Playbook](./incident-response-playbook.md)
- [Runbook Collection](./runbooks/)
- [API Documentation](./api-documentation.md)
