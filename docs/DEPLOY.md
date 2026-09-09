# デプロイ

## 構成

単一コンテナ。FastAPI が API と**ビルド済みフロントエンドの両方**を配信するので、
本番ではブラウザから見えるオリジンは 1 つだけになり CORS は不要です。

```
Dockerfile
├─ stage 1 (node:24-slim)   pnpm build           -> frontend/dist
└─ stage 2 (python:3.13-slim)
   ├─ /app/app/            FastAPI パッケージ
   ├─ /app/data/words.txt  辞書 (dictionary.py が parents[2]/data を見る)
   ├─ /app/app/static/     stage 1 の dist (config.py が app/static を見る)
   └─ uvicorn --port 7860  (Hugging Face Spaces が転送するポート)
```

`app/static/index.html` が存在するときだけ `/` にマウントされます。開発時は
`vite dev` + `dev.sh` のままで、静的配信は行われません。

## 環境変数

`backend/.env.example` を `backend/.env` にコピーして埋めます（`.env` は gitignore 済み、
`python-dotenv` が読み込みます）。デプロイ先では同じ名前を実際の環境変数 / Secret として
渡します（実環境変数が `.env` より優先されます）。

| 変数 | 既定 | 意味 |
|------|------|------|
| `IBM_QUANTUM_TOKEN` | (なし) | これが無い間は**シミュレータのみ**で動作し、実機パネルは描画されません |
| `IBM_QUANTUM_INSTANCE` | (なし) | 有償/組織インスタンスの CRN。Open Plan は空でよい |
| `IBM_QUANTUM_CHANNEL` | `ibm_quantum_platform` | `ibm_cloud` / `local` も指定可 |
| `IBM_QUANTUM_BACKEND` | (なし) | デバイス固定。空なら稼働中の least busy QPU |
| `IBM_QUANTUM_SHOTS` | `1024` | 上限 4096 |
| `IBM_QUANTUM_MAX_JOBS_PER_HOUR` | `3` | プロセス全体の投入上限 |
| `IBM_QUANTUM_MAX_JOBS_PER_DAY` | `6` | 同上 |
| `HARDWARE_ENABLED` | `1` | `0` にすると認証情報を残したまま実機モードだけ止められる |
| `ALLOWED_ORIGINS` | dev の localhost 2 つ | フロントを別オリジンから出す場合のみ |
| `STATIC_DIR` | `app/static`（あれば） | 静的ファイルの場所を明示したいとき |

### QPU 枠の見積もり（実測ベース）

IBM Quantum の Open Plan は月あたり約 10 分 = 600 秒の QPU 時間です。`ibm_marrakesh` で
測ったところ、縮約後のジョブ 1 件の課金時間（`usage.qpu_charge_time_seconds`）は **2 秒**
でした。既定の「1 日 6 件」は月あたり約 180 件 ≒ 360 秒で、上限まで使われても枠の
6 割程度に収まります。

**公開デプロイでは 1 つのトークンを訪問者全員が共有する**ため、上限はセッション単位では
なくプロセス全体で数えています（`app/quantum/jobs.py`）。枠を使い切りたくない場合は
`HARDWARE_ENABLED=0` で止めるか、上限を下げてください。

投入から結果までの実時間はキュー次第で、実測では 12 秒と 74 秒でした。空いていれば
速いですが、混雑時は数十分かかり得るのでフロントはポーリングで待ちます。

## ホスティング先の選定（2026-09 時点の調査結果）

| 候補 | 無料枠 | カード | 判定 |
|---|---|---|---|
| Hugging Face Docker Space | **廃止**（無料は static のみ、Docker は PRO $9/月） | — | ✗ |
| Koyeb | **廃止**（無料は Postgres 5 時間のみ） | — | ✗ |
| Fly.io | なし（256 MB で約 $2〜3/月） | 必須 | ✗ |
| Google Cloud Run | あり | 必須 | △ |
| Northflank Sandbox | サービス 2 つ・**常時稼働** | 必須 | △ RAM 非公開 |
| **Render 無料** | **750 時間/月** | 記載なし | **採用** |

ゲーム状態がインメモリなので常駐プロセスが 1 つ必要で、これが Vercel / Netlify /
Cloudflare のサーバーレスを（バンドルサイズ以前に）失格にします。PythonAnywhere 無料は
外向き通信がホワイトリスト制で IBM Quantum API に届かないため同様に不可です。

実測ピーク RSS は **156 MB**（起動 105 MB → Grover k=50 で 139 MB → 回路 SVG で 156 MB）
なので、Render の 512 MB には余裕を持って収まります。

## Render（無料・推奨）

`render.yaml` が Blueprint として置いてあります。0.1 CPU / 512 MB、750 インスタンス時間/月、
15 分無通信でスリープ・復帰約 1 分、ファイルシステムは揮発（インメモリのゲーム状態は
スリープで消えますが、一座で遊ぶ分には影響しません）。

1. <https://dashboard.render.com> で **New → Blueprint** を選び、このリポジトリを指定
2. `IBM_QUANTUM_TOKEN` の入力を求められるので貼る（空のままならシミュレータのみで動作し、
   実機パネルは自動的に隠れます）
3. Apply。初回はフロントの `pnpm build` と qiskit 群の `pip install` が走るため数分かかります
4. 払い出された URL（`https://<name>.onrender.com`）を、GitHub の
   Settings → Secrets and variables → Actions → **Variables** に `RENDER_URL` として登録

`sync: false` の環境変数は **Blueprint 作成時にしか聞かれない**ので、後から変える場合は
サービスの Environment 画面で直接編集します。

### スリープ対策（keep-warm）

`.github/workflows/keep-warm.yml` が 10 分おきに `/healthz` を叩きます。動かす時間帯を
08:00–23:59 JST に絞っているのは枠の都合です: 750 時間/月に対して 31 日は 744 時間なので、
24 時間叩き続けると枠をほぼ使い切り、超過すると翌月までサービスが停止します。16 時間/日なら
約 496 時間/月で余裕があります。

GitHub のスケジュール実行は best-effort で 15 分以上遅れることがあるため、「たいてい温かい」
程度の保証です。またリポジトリに 60 日間活動が無いとスケジュールは自動停止します。

## Hugging Face Spaces（PRO 契約がある場合）

`deploy/hf_space.py` がそのまま使えます。無料 cpu-basic では 402 が返るため PRO が必要です。

```bash
pip install huggingface_hub
HF_TOKEN=hf_xxx IBM_QUANTUM_TOKEN=xxx \
  python deploy/hf_space.py <owner>/quantum-wordle
```

スクリプトは Space を作成（既にあれば再利用）し、`IBM_QUANTUM_TOKEN` を Space Secret に、
その他の `IBM_QUANTUM_*` を Space Variable として登録し、Dockerfile が必要とする
ファイルだけをアップロードします。`.venv` / `node_modules` / `dist` / `.env` は
staging の段階で除外されるため送信されません。トークンが git remote に書き込まれることも
ありません。`--dry-run` で送信内容だけ確認、`--private` で非公開 Space。

## コンテナをローカルで動かす

Podman でも Docker でもコマンドは同じです（`podman` を `docker` に読み替え）。

```bash
podman build -t quantum-wordle:local .
podman run --rm -p 7860:7860 --env-file backend/.env quantum-wordle:local
# http://127.0.0.1:7860
```

確認済みの挙動:

- イメージ 608 MB、`useradd` した uid 1000 の非 root で起動する
- `--env-file` を渡さないと `hardware: false` を返し、実機パネルは描画されない（縮退動作）
- `-e PORT=10000` で待ち受けポートが変わる（Render が注入するのと同じ経路）

Apple Silicon では arm64 でビルドされます。Render は amd64 なので wheel の実体は異なりますが、
依存解決の破綻は `make deps-check` の方が速く捕まえられます。amd64 で確かめたい場合は
`--platform linux/amd64` を付けられますが、エミュレーションで大幅に遅くなります。

## Docker を使わずに本番配置を再現する

```bash
cd frontend && pnpm build && cd ..
rm -rf backend/app/static && cp -r frontend/dist backend/app/static
cd backend && .venv/bin/uvicorn app.main:app --port 8000
```

`backend/app/static/` は gitignore 済みなので、コミットに混ざりません。

## フロントを別オリジンへ分ける場合

単一コンテナをやめてフロントを Vercel などに置くなら、`ALLOWED_ORIGINS` にそのオリジンを
設定し、フロント側の `/api` プロキシを API の実 URL に向けます。同一オリジンで済むうちは
分ける利点はありません。
