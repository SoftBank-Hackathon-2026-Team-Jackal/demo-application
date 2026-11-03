# Cloud Migration Demo Application

하나의 저장소에 원본 애플리케이션과 시각화 웹을 분리했다. 메시지는 PostgreSQL에 저장되고, 별도 트래픽 발생기가 지속해서 쓰기를 보낸다. 웹은 읽기 전용이며 2초마다 최근 메시지와 총 건수를 갱신한다.

## 구조

| 경로 | 역할 |
| --- | --- |
| `apps/api/` | FastAPI 메시지 API, PostgreSQL 스키마·연결, 비활성 S3 코드, 컨테이너 이미지 |
| `apps/web/` | Vercel에 배포할 React/Vite 화면과 읽기 전용 API 프록시 |
| `tools/traffic.py` | 초기 100건 생성 및 지속 쓰기, 성공 응답 원장 기록 |
| `tools/verify.py` | 원장의 각 메시지가 이전 대상 API에 같은 ID·본문으로 존재하는지 확인 |
| `tools/create_edge.py` | 도메인 없이 CloudFront 기본 HTTPS 주소를 ALB 앞에 생성 |
| `infra/k8s/source.yaml` | 원본 EKS의 Namespace·ConfigMap·Service·PostgreSQL·PVC·앱·Ingress |
| `compose.yaml` | 로컬 PostgreSQL 16과 API 실행 |

## 데이터 계약

`messages(id UUID PK, request_id UUID UNIQUE, body VARCHAR(200), created_at TIMESTAMPTZ)`를 사용한다. `POST /api/messages`는 `X-Demo-Write-Token`이 필요하며 같은 `request_id` 재요청은 기존 메시지를 반환한다. `GET /api/messages?limit=30`은 최근 목록과 전체 건수를 반환하고, `GET /api/messages/{id}`는 이전 검증에 사용한다. `GET /health`는 PostgreSQL 연결을 확인한다.

원본 DB는 `wal_level=logical`, `max_replication_slots=4`, `max_wal_senders=4`로 시작한다. 스키마는 앱 시작 시 `CREATE TABLE IF NOT EXISTS`로 준비한다. 실제 복제·정합성·쓰기 전환은 마이그레이션 플랫폼이 담당한다. S3 어댑터 코드는 유지하지만 `S3_ENABLED=false`이므로 앱용 버킷과 객체 이전은 데모에서 제외한다.

## 로컬 실행

1. `.env.example`을 `.env`로 복사하고 `DB_PASSWORD`, `DEMO_WRITE_TOKEN`에 임의의 강한 값을 넣는다.
2. `docker compose up --build -d` 실행 후 `curl http://localhost:8080/health`로 확인한다.
3. `cd apps/web && npm ci && npm run dev`로 화면을 실행한다. Vite가 로컬 `/api` 요청을 `localhost:8080`으로 전달한다.
4. `DEMO_WRITE_TOKEN=<토큰> python3 tools/traffic.py --url http://localhost:8080 --seed 100`으로 초기 데이터를 만든다. `--seed`를 생략하면 초당 1건을 계속 기록한다. 성공 응답은 `traffic-ledger.jsonl`에 저장한다.

## 배포 원칙

- 원본은 `ap-northeast-2` EKS의 `demo-source` Namespace, 앱 1 Pod(250m/256Mi), PostgreSQL 16 1 Pod(500m/1Gi), 10Gi EBS PVC다.
- 이미지는 `linux/amd64`로 빌드해 ECR에 올리고 반환된 Digest URI를 배포에 사용한다. Sandbox와 이전 대상에도 그 Digest를 넘긴다.
- `.env` 원문이나 Secret은 저장소·이미지·Vercel에 넣지 않는다. Vercel은 읽기 전용 프록시에 백엔드 주소 `BACKEND_ORIGIN`만 사용한다.
- `AWS_PROFILE=cmp-aws-prod eksctl create cluster -f infra/eks/cluster.yaml`로 전용 원본 클러스터를 준비한다. 클러스터의 AWS Load Balancer Controller를 설치한 뒤 `infra/eks/deploy-source.sh <ECR Digest URI>`로 Secret과 매니페스트를 적용한다.
- `tools/verify.py --target-url <대상 API> --ledger traffic-ledger.jsonl`은 성공 응답을 받은 모든 ID와 본문을 대상에서 확인한다.
- ALB 주소가 준비되면 `apps/api/.venv/bin/python tools/create_edge.py --origin <ALB DNS>`로 기본 HTTPS 주소를 만든다. Vercel의 `BACKEND_ORIGIN`에는 이 HTTPS 주소를 설정한다.

데모용 AWS 네트워크는 소스 VPC `10.20.0.0/16`, 서로 다른 두 AZ의 Public·Private 서브넷, 노드 `t3.medium` 2대를 기준으로 한다. `eksctl`이 각 서브넷을 `/19`로 자동 할당한다. 별도 도메인·인증서가 없으므로 CloudFront 기본 HTTPS 주소에서 TLS를 종료하고 ALB는 HTTP 원본으로 사용한다. Vercel 화면도 HTTPS이며 서버 함수가 CloudFront API를 프록시한다.
