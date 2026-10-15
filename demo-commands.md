## 0. Перевірка кластера

```powershell
minikube status
kubectl get nodes -o wide
minikube addons list | Select-String "metrics-server|ingress"
kubectl get pods -n kube-system
minikube image ls | Select-String runedrive
```

## 1. Kubernetes-маніфести (k8s/)

### 1.1. Зняти Helm-реліз, якщо він встановлений

```powershell
helm uninstall runedrive -n runedrive
kubectl delete namespace runedrive --timeout=90s
```

### 1.2. Розгортання з маніфестів

```powershell
kubectl apply -f k8s/
kubectl rollout status deployment/runedrive-api -n runedrive --timeout=180s
kubectl get pods,svc,pvc,ingress -n runedrive -o wide
```

### 1.3. Health check та заголовок інстансу

Термінал 1:

```powershell
kubectl port-forward svc/runedrive-api 8080:80 -n runedrive
```

Термінал 2:

```powershell
curl.exe -s http://127.0.0.1:8080/api/v1/health
1..20 | ForEach-Object { curl.exe -s -D - http://127.0.0.1:8080/api/v1/health | Select-String "x-instance-id" } | Group-Object | Select-Object Count, Name
```

### 1.4. Балансування всередині кластера

```powershell
kubectl run curl-lb --image=curlimages/curl --restart=Never -n runedrive --command -- sh -c 'for i in $(seq 1 20); do curl -s -D - http://runedrive-api/api/v1/health | grep -i x-instance-id; done'
kubectl wait --for=condition=Ready pod/curl-lb -n runedrive --timeout=60s
kubectl logs curl-lb -n runedrive | Group-Object | Sort-Object Name | Select-Object Count, Name
kubectl delete pod curl-lb -n runedrive --ignore-not-found
```

### 1.5. Self-healing

```powershell
$pod = kubectl get pods -n runedrive -l app=runedrive-api -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $pod -n runedrive
kubectl rollout status deployment/runedrive-api -n runedrive
kubectl get pods -n runedrive
```

### 1.6. Горизонтальне масштабування

```powershell
kubectl scale deployment/runedrive-api --replicas=4 -n runedrive
kubectl wait --for=condition=available deployment/runedrive-api -n runedrive --timeout=120s
kubectl get pods -n runedrive
kubectl scale deployment/runedrive-api --replicas=2 -n runedrive
kubectl wait --for=condition=available deployment/runedrive-api -n runedrive --timeout=120s
```

### 1.7. Метрики

```powershell
kubectl top nodes
kubectl top pods -n runedrive
```

### 1.8. Rolling update та відкат

```powershell
kubectl set image deployment/runedrive-api api=runedrive:1.1.0 -n runedrive
kubectl rollout status deployment/runedrive-api -n runedrive
kubectl rollout history deployment/runedrive-api -n runedrive
kubectl rollout undo deployment/runedrive-api -n runedrive
kubectl rollout status deployment/runedrive-api -n runedrive
```

### 1.9. Ingress

Термінал від адміністратора:

```powershell
minikube tunnel
```

Далі у звичайному терміналі:

```powershell
curl.exe -H "Host: runedrive.local" http://127.0.0.1/api/v1/health
```

Без тунелю, зсередини кластера:

```powershell
kubectl run curl-ing --rm -i --image=curlimages/curl --restart=Never -n runedrive -- curl -s -H "Host: runedrive.local" http://ingress-nginx-controller.ingress-nginx/api/v1/health
```

### 1.10. Прибрати реліз перед демо Helm

```powershell
kubectl delete namespace runedrive --timeout=90s
kubectl wait --for=delete namespace/runedrive --timeout=120s
```

## 2. Helm-чарт (helm/runedrive)

### 2.1. Валідація чарта

```powershell
helm lint helm/runedrive
helm lint helm/runedrive -f helm/runedrive/values-prod.yaml
helm template runedrive helm/runedrive
helm template runedrive helm/runedrive -f helm/runedrive/values-prod.yaml | Select-String "ingress|resources"
```

### 2.2. Встановлення релізу

```powershell
helm install runedrive helm/runedrive -n runedrive --create-namespace
helm list -n runedrive
helm status runedrive -n runedrive
kubectl get pods,svc,pvc,ingress -n runedrive
```

### 2.3. Тест релізу

```powershell
helm test runedrive -n runedrive
```

### 2.4. Оновлення версії застосунку

```powershell
helm upgrade runedrive helm/runedrive --set image.tag=1.1.0 -n runedrive
kubectl rollout status deployment/runedrive-runedrive-api -n runedrive
kubectl get pods -n runedrive -o wide
helm history runedrive -n runedrive
```

### 2.5. Відкат

```powershell
helm rollback runedrive 1 -n runedrive
kubectl rollout status deployment/runedrive-runedrive-api -n runedrive
helm history runedrive -n runedrive
```

### 2.6. Апгрейд на prod-профіль

```powershell
helm upgrade runedrive helm/runedrive -f helm/runedrive/values-prod.yaml -n runedrive
kubectl rollout status deployment/runedrive-runedrive-api -n runedrive
kubectl get ingress -n runedrive
kubectl get deploy runedrive-runedrive-api -n runedrive -o jsonpath='{.spec.template.spec.containers[0].resources}'
helm history runedrive -n runedrive
```

### 2.7. Видалення релізу

```powershell
helm uninstall runedrive -n runedrive
kubectl get pods -n runedrive
```

## 3. Швидка перевірка (копіювати блоком цілком)

```powershell
$ns = 'runedrive'
minikube status
kubectl get nodes -o wide
helm uninstall runedrive -n $ns --ignore-not-found 2>$null
kubectl delete namespace $ns --ignore-not-found --timeout=120s
kubectl wait --for=delete namespace/$ns --timeout=120s
kubectl apply -f k8s/
kubectl rollout status deployment/runedrive-api -n $ns --timeout=180s
kubectl rollout status deployment/postgres -n $ns --timeout=120s
kubectl rollout status deployment/redis -n $ns --timeout=120s
kubectl get pods,svc,pvc,ingress -n $ns -o wide
kubectl delete pod curl-lb -n $ns --ignore-not-found
kubectl run curl-lb --image=curlimages/curl --restart=Never -n $ns --command -- sh -c 'for i in $(seq 1 20); do curl -s -D - http://runedrive-api/api/v1/health | grep -i x-instance-id; done'
kubectl wait --for=condition=Ready pod/curl-lb -n $ns --timeout=60s
kubectl logs curl-lb -n $ns | Group-Object | Sort-Object Name | Select-Object Count, Name
kubectl delete pod curl-lb -n $ns --ignore-not-found
$pod = kubectl get pods -n $ns -l app=runedrive-api -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $pod -n $ns
kubectl rollout status deployment/runedrive-api -n $ns --timeout=120s
kubectl scale deployment/runedrive-api --replicas=4 -n $ns
kubectl wait --for=condition=available deployment/runedrive-api -n $ns --timeout=120s
kubectl get pods -n $ns -l app=runedrive-api
do { Start-Sleep -Seconds 10; $top = kubectl top pods -n $ns 2>$null } until ($top)
$top
kubectl scale deployment/runedrive-api --replicas=2 -n $ns
kubectl wait --for=condition=available deployment/runedrive-api -n $ns --timeout=120s
kubectl set image deployment/runedrive-api api=runedrive:1.1.0 -n $ns
kubectl rollout status deployment/runedrive-api -n $ns --timeout=180s
kubectl rollout history deployment/runedrive-api -n $ns
kubectl rollout undo deployment/runedrive-api -n $ns
kubectl rollout status deployment/runedrive-api -n $ns --timeout=180s
kubectl delete namespace $ns --timeout=120s
kubectl wait --for=delete namespace/$ns --timeout=120s
helm lint helm/runedrive
helm install runedrive helm/runedrive -n $ns --create-namespace
helm test runedrive -n $ns
helm upgrade runedrive helm/runedrive --set image.tag=1.1.0 -n $ns
kubectl rollout status deployment/runedrive-runedrive-api -n $ns --timeout=180s
helm history runedrive -n $ns
helm rollback runedrive 1 -n $ns
kubectl rollout status deployment/runedrive-runedrive-api -n $ns --timeout=180s
helm upgrade runedrive helm/runedrive -f helm/runedrive/values-prod.yaml -n $ns
kubectl rollout status deployment/runedrive-runedrive-api -n $ns --timeout=180s
kubectl get ingress -n $ns
kubectl get deploy runedrive-runedrive-api -n $ns -o jsonpath='{.spec.template.spec.containers[0].resources}'
helm uninstall runedrive -n $ns
kubectl get pods -n $ns
```
