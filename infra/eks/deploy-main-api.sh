#!/usr/bin/env bash
set -euo pipefail

if [[ "${GITHUB_REF:-}" != "refs/heads/main" ]]; then
  echo "deploy from main only" >&2
  exit 2
fi
: "${GITHUB_SHA:?missing GITHUB_SHA}"
: "${GITHUB_RUN_ID:?missing GITHUB_RUN_ID}"
: "${GITHUB_RUN_ATTEMPT:?missing GITHUB_RUN_ATTEMPT}"

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ "$(git -C "$repo_root" rev-parse HEAD)" != "$GITHUB_SHA" ]]; then
  echo "checked-out commit differs from GITHUB_SHA" >&2
  exit 2
fi

region="ap-northeast-2"
account="714066696240"
cluster="cmp-demo-source"
registry="$account.dkr.ecr.$region.amazonaws.com"
repository="$registry/cmp-demo-api"
tag="main-${GITHUB_SHA:0:12}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
if [[ "$(aws sts get-caller-identity --query Account --output text)" != "$account" ]]; then
  echo "unexpected AWS account" >&2
  exit 2
fi

deploy_tmp_dir="$(mktemp -d)"
trap 'rm -rf "$deploy_tmp_dir"' EXIT
aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin "$registry"
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  --tag "$repository:$tag" \
  --metadata-file "$deploy_tmp_dir/build.json" \
  --push "$repo_root/apps/api"

digest="$(python3 - "$deploy_tmp_dir/build.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as metadata_file:
    print(json.load(metadata_file).get("containerimage.digest", ""))
PY
)"
if [[ ! "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]; then
  echo "build did not return a valid image digest" >&2
  exit 1
fi
image_uri="$repository@$digest"

kubeconfig="$deploy_tmp_dir/kubeconfig"
aws eks update-kubeconfig --region "$region" --name "$cluster" --kubeconfig "$kubeconfig"
KUBECONFIG="$kubeconfig" kubectl -n demo-source set image deployment/demo-api "api=$image_uri"
KUBECONFIG="$kubeconfig" kubectl -n demo-source rollout status deployment/demo-api --timeout=300s
deployed_image="$(KUBECONFIG="$kubeconfig" kubectl -n demo-source get deployment demo-api -o jsonpath='{.spec.template.spec.containers[?(@.name=="api")].image}')"
if [[ "$deployed_image" != "$image_uri" ]]; then
  echo "deployment image does not match pushed digest" >&2
  exit 1
fi
curl -fsS --retry 5 --retry-delay 3 --retry-all-errors --max-time 15 \
  https://d2zci3wn74hrb.cloudfront.net/health
echo
echo "deployed $image_uri"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  printf 'Deployed `%s` to `%s/demo-source` from main commit `%s`.\n' \
    "$image_uri" "$cluster" "$GITHUB_SHA" >> "$GITHUB_STEP_SUMMARY"
fi
