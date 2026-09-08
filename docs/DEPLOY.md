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

## Hugging Face Spaces（無料・推奨）

無料の CPU basic は 2 vCPU / 16 GB なので、qiskit + aer + matplotlib の依存でも余裕があります。
無料 Space は公開で、長期間アクセスが無いとスリープし、次のアクセスで復帰します。

1. <https://huggingface.co/settings/tokens> で **write** 権限のトークンを作る
2. 実行:

```bash
pip install huggingface_hub
HF_TOKEN=hf_xxx IBM_QUANTUM_TOKEN=xxx \
  python deploy/hf_space.py <owner>/quantum-wordle
```

スクリプトは Space を作成（既にあれば再利用）し、`IBM_QUANTUM_TOKEN` を Space Secret に、
その他の `IBM_QUANTUM_*` を Space Variable として登録し、Dockerfile が必要とする
ファイルだけをアップロードします。`.venv` / `node_modules` / `dist` / `.env` は
staging の段階で除外されるため送信されません。トークンが git remote に書き込まれることも
ありません。

`--dry-run` で送信内容だけ確認できます。`--private` で非公開 Space。

`IBM_QUANTUM_TOKEN` を渡さなければシミュレータのみでデプロイされ、後から Space の
Settings → Variables and secrets で追加すれば実機モードが有効になります。

## Docker をローカルで動かす

```bash
docker build -t quantum-wordle .
docker run --rm -p 7860:7860 --env-file backend/.env quantum-wordle
# http://127.0.0.1:7860
```

## Docker を使わずに本番配置を再現する

```bash
cd frontend && pnpm build && cd ..
rm -rf backend/app/static && cp -r frontend/dist backend/app/static
cd backend && .venv/bin/uvicorn app.main:app --port 8000
```

`backend/app/static/` は gitignore 済みなので、コミットに混ざりません。

## Render を使う場合

無料 Web Service は 512 MB RAM・15 分アイドルでスリープ（復帰に 1 分程度）で、
qiskit + matplotlib には余裕がありません。使うなら同じ Dockerfile を指定し、
`--port $PORT` に合わせて `CMD` を上書きしてください。フロントを Vercel などへ分ける場合は
`ALLOWED_ORIGINS` にそのオリジンを設定し、フロント側の `/api` プロキシを実 URL に向けます。
