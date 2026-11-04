# 데모 백엔드 수동 배포

GitHub의 `Deploy demo API` 워크플로는 **수동 실행(`workflow_dispatch`)만** 지원한다. `main`을 선택해야 배포 Job이 실행된다. 실행 시 그 커밋의 `apps/api`를 `linux/amd64`로 빌드하고, ECR `cmp-demo-api`에 실행별 고유 태그로 push한 다음 반환된 SHA-256 Digest를 EKS `cmp-demo-source`의 `demo-source/demo-api` Deployment에 적용한다. Rollout과 공개 `/health`를 확인한다. DB, Secret, Vercel, CloudFront 리소스는 갱신하지 않는다.

## GitHub에서 실행

1. 변경 PR을 `main`에 병합한다.
2. `Actions` → `Deploy demo API` → `Run workflow`에서 Branch를 `main`으로 선택해 실행한다.
3. 실행 로그의 이미지 Digest와 마지막 `deployed ...` 메시지, Job Summary를 확인한다.

CLI를 쓰려면 `gh workflow run deploy-api.yml --ref main`을 실행한다. 워크플로 파일이 `main`에 병합되기 전에는 GitHub Actions 화면의 수동 실행 메뉴에 나타나지 않는다.

## 권한 및 초기 설정

- GitHub OIDC 역할 `cmp-demo-github-deployer`는 이 저장소의 `main` ref만 신뢰한다. 정책 파일은 `infra/eks/github-deployer-trust.json`과 `github-deployer-policy.json`이다. AWS 장기 키를 GitHub Secret에 넣지 않는다.
- IAM 정책은 ECR `cmp-demo-api` push와 EKS `cmp-demo-source` 조회만 허용한다.
- EKS Access Entry는 해당 역할을 Kubernetes 그룹 `cmp-demo-deployers`에 매핑한다. `infra/k8s/github-deployer-rbac.yaml`이 `demo-source/demo-api` Deployment의 조회·패치·watch만 허용한다.
- 기존 클러스터에 IAM 역할, EKS Access Entry, RBAC를 적용해야 GitHub 배포가 동작한다. 새 클러스터를 만들 경우에도 이 연결을 다시 설정한다.

## 실패 시 확인

- OIDC 실패: `main` 선택 여부와 IAM 역할의 `sub` 조건을 확인한다.
- ECR push 실패: 계정·리전·역할 정책과 저장소를 확인한다.
- EKS 접근 실패: Access Entry의 그룹과 RoleBinding을 확인한다.
- Rollout 실패: `kubectl -n demo-source describe deployment demo-api`와 새 Pod 이벤트를 확인한다. 기존 이미지로 되돌릴 때는 이전에 기록한 Digest URI를 `kubectl -n demo-source set image deployment/demo-api api=<이전 Digest URI>`로 적용한다.
