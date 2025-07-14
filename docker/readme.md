# Only run this section if you want to deploy the app within AKS via streamlit

## Prerequisites

1. AI foundry project
2. gpt-4.1 and gpt-4.1-mini deployed
3. Azure container registry created
4. Grant acr pull and acr push permissions to mi-tenant-a and mi-tenant-b

## Create the docker image

Open a terminal in your local system. Substitute with your own repository.

```bash
az acr --login <repo name>.azurecr.io
docker build docker/. -t <repo name>.azurecr.io/multitenant-ai:latest
docker push <repo name>.azurecr.io/multitenant-ai:latest
```

# Update the manifests file for both tenanta and tenantb with your repo name

```yaml
containers:
    - name: semantic-ui
    image: <repo_name>.azurecr.io/multitenant-ai:latest
```

# Deploy the manifest file

```bash
kubectl apply -f ./docker/manifests/tenanta/deployment.yaml -n tenant-a
kubectl apply -f ./docker/manifests/tenantb/deployment.yaml -n tenant-b
```

# Access the streamlit UI for tenant-a

```bash
kubectl port-forward svc/tenant-a-streamlit-service 8501:8501 -n tenant-a
```

Here is a sample command for you to type into the chat box. You can see the function invocation logs section to see which agent was called, which function was triggered and what the argurments specified are.

```bash
plan me an itinerary to singapore for 3 days
```

![streamlit.png](streamlit.png)