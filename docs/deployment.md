# 원본 데모 배포 기록

## 원본 환경

- AWS 프로필: `cmp-aws-prod`, 계정: `714066696240`, 리전: `ap-northeast-2`
- EKS 클러스터: `cmp-demo-source`, Namespace: `demo-source`
- 노드: `t3.medium` 2대, PostgreSQL 16: 1 Pod와 10Gi PVC, API: 1 Pod
- API 이미지: `714066696240.dkr.ecr.ap-northeast-2.amazonaws.com/cmp-demo-api@sha256:b4e569f873f9e4c10e321a817dddef01c92d6076d412471cb288f604cf84eef2`
- 공개 HTTPS API: `https://d2zci3wn74hrb.cloudfront.net`
- ALB 원본: `k8s-demosour-demoapi-05244864b1-1825845645.ap-northeast-2.elb.amazonaws.com` (`HTTP:80`)
- CloudFront 배포 ID: `E13K0WD07TYWNV`

CloudFront에서 HTTPS를 종료하고 ALB 원본에는 HTTP로 연결한다. DB Service는 클러스터 내부에서만 접근한다. API Pod의 송신은 DB Pod의 TCP 5432 및 CoreDNS의 TCP/UDP 53으로 제한한다.

## 확인한 항목

- `/health`가 DB 연결 검사와 함께 `{"status":"ok"}`를 반환했다.
- 원본 DB의 `wal_level=logical`, `max_replication_slots=4`, `max_wal_senders=4`를 확인했다.
- 초기 메시지 100건을 HTTPS API로 전송했고, 응답 원장의 ID·본문 100건이 원본 API와 모두 일치했다.
- EKS VPC CNI 애드온이 `ACTIVE`이고 NetworkPolicy가 생성됐다. API Pod에서 DB Service DNS 조회는 성공했고 외부 주소 `1.1.1.1:443` 연결은 실패했다. 정책 적용 뒤에도 `/health`와 100건 검증이 통과했다.
- 이 검증은 **원본 환경**에 관한 것이다. 대상 환경으로의 복제·쓰기 전환·이전 후 정합성 검사는 아직 수행하지 않았다.

## 프론트 상태

`apps/web`은 로컬 빌드 및 API 프록시 확인을 마쳤다. Vercel `kimminseo-s-projects/cmp-demo-application`에 로컬 CLI로 배포했으며 Git 저장소 연결은 설정하지 않았다. 사용자 승인에 따라 프로젝트의 SSO 배포 보호를 해제했다. 공개 화면 주소는 `https://cmp-demo-application.vercel.app`이며, 로그인 없는 요청에서 화면과 `/api/messages?limit=1`이 모두 HTTP 200을 반환하고 총 100건을 표시하는 것을 확인했다.

## 재확인

```bash
AWS_PROFILE=cmp-aws-prod aws eks update-kubeconfig --region ap-northeast-2 --name cmp-demo-source
kubectl -n demo-source get deploy,sts,pod,pvc,ingress,networkpolicy
curl -fsS https://d2zci3wn74hrb.cloudfront.net/health
curl -fsS 'https://d2zci3wn74hrb.cloudfront.net/api/messages?limit=1'
python3 tools/verify.py --target-url https://d2zci3wn74hrb.cloudfront.net --ledger traffic-ledger-source.jsonl
```

`traffic-ledger-source.jsonl`은 로컬 생성 산출물로 Git에 포함되지 않는다. `verify.py`의 대상 URL을 마이그레이션 후 대상 API로 바꾸면 원본에서 성공 응답을 받은 메시지를 대상과 대조할 수 있다.

이번 클러스터에서는 CNI 애드온 업데이트 중 `aws-node` 서비스 계정의 IRSA 역할 주석이 빠져 CNI Pod가 준비되지 않았다. 애드온이 생성한 `serviceAccountRoleArn`을 `aws-node`에 연결하고 DaemonSet을 재시작한 후 애드온이 `ACTIVE`가 됐다. 새 클러스터를 만들 때는 `infra/eks/cluster.yaml`의 CNI 충돌 해결 설정을 사용하고, `aws-node` 서비스 계정의 역할 주석과 DaemonSet 준비 상태를 확인한다.
