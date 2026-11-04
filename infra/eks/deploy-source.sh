#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <ECR image URI pinned to sha256 digest>" >&2
  exit 2
fi
image_uri="$1"
if [[ "$image_uri" != *@sha256:* ]]; then
  echo "image URI must be pinned to a sha256 digest" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ ! -f "$repo_root/.env" ]]; then
  echo "create $repo_root/.env from .env.example first" >&2
  exit 2
fi

context="$(kubectl config current-context)"
if [[ "$context" != *"cmp-demo-source"* ]]; then
  echo "refusing to deploy to unexpected kubectl context: $context" >&2
  exit 2
fi

kubectl apply -f "$repo_root/infra/k8s/source.yaml" --dry-run=client -o name >/dev/null
kubectl create namespace demo-source --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic demo-api-secrets \
  --namespace demo-source \
  --from-env-file="$repo_root/.env" \
  --dry-run=client -o yaml | kubectl apply -f -
sed "s|IMAGE_URI_REPLACE_ME|$image_uri|g" "$repo_root/infra/k8s/source.yaml" | kubectl apply -f -
kubectl rollout status statefulset/demo-db -n demo-source --timeout=300s
kubectl rollout status deployment/demo-api -n demo-source --timeout=300s
kubectl get ingress demo-api -n demo-source
