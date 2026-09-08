# TODO

## Phase 1 — Frontend基礎
✅ React + TypeScript + Tailwind (Vite)
✅ Wordle盤面 (フリップ演出, reduced-motion対応)
✅ キーボード (画面 + 物理, 文字状態の色反映)
✅ 候補空間パネル (logスケールメーター + 候補チップ)

## Phase 2 — Backend基盤
✅ FastAPI雛形 + 統一エラーハンドラ + CORS
✅ Feedback判定 (本家準拠, golden tests)
✅ 候補フィルタ (履歴整合性)
✅ ゲームAPI (games / guesses / candidates)
✅ インメモリState (TTL付き, Protocol経由)
✅ 辞書 (SGB頻度順 上位2315語)
✅ フロントエンドはAPI接続のみで実装 (判定ロジックはバックエンドに一元化)

## Phase 3 — Quantum Engine (シミュレータ)
✅ インデックスエンコーディング (12 qubits, 辞書index = 基底状態)
✅ 初期重ね合わせは全4096状態に決定 (辞書外状態が増幅されない様子も教材化)
✅ 候補集合Oracle (DiagonalGate位相オラクル, 正解を知らない)
✅ QuantumBackend抽象 (Protocol) + AerStatevectorBackend
✅ POST /quantum/run (iteration 0..k の確率スナップショット一括返却)

## Phase 4 — Grover体験
✅ Diffusion含む完全なGroverループ (Phase 3エンジンで実装済み)
✅ 反復スライダー (最適k*表示, 3k*まで over-rotation 体験可能)
✅ 確率分布アニメーション (反復再生 + スクラバー + P(候補)スパークライン)
✅ POST /quantum/measure (shots対応, 辞書外/候補外の結果も正直に表示)
✅ 測定結果を推測入力欄へ送るフロー (ターンは消費しない)

## Phase 5 — 発展
✅ 回路図表示 (Qiskit mpl描画のSVGをAPIで配信, H⊗12 + Oracle/Diffusionブロック)
✅ 演出強化 (測定結果のcollapseアニメーション, reduced-motion対応)
✅ IBM Quantum実機バックエンド — ハイブリッド構成で実装。ゲーム進行とスナップショットはAerのまま、実機は「縮約Groverでノイズを見る」パネルとして追加 (D4/リスク表の方針どおり)
  - 12qubit DiagonalGateは実機では深すぎるため、候補上位4語を2〜4qubitに詰め直し候補割合1/4 → k*=1 の浅い回路に縮約 (`app/quantum/hardware.py`)
  - オラクルは多重制御Zで再構成。既存のDiagonalGate回路と同一ユニタリであることをテストで検証
  - SamplerV2で投入 → 202でjob_id即返却 → フロントがバックオフ付きポーリング (キュー待ち数分〜数十分に耐える)
  - QPU無料枠(月約10分)を守るため、プロセス全体の投入上限をレート制限として実装 (`app/quantum/jobs.py`)

## Phase 6 — 仕上げ
✅ チュートリアル文言 (誤概念対策) — 初回自動表示 + ヘッダー「使い方」で再表示。5ステップで「Groverは答えを知らない」「候補を絞るのはあなた」「over-rotation」を伝える。localStorageで既読記憶、Esc/背景クリックで閉じる、reduced-motion対応
✅ README最終化 — 起動手順・辞書出典・アーキテクチャ図・チュートリアル節・UIレイアウト図を整備。Project Status を Phase 6 完了に更新
⏭ スクリーンショット — 実物撮影は見送り (README内テキストのUIレイアウト図で代替)
✅ Docker — 単一コンテナ (FastAPIがAPI + ビルド済みフロントを同一オリジンで配信, CORS不要)

## Phase 7 — デプロイ
✅ Dockerfile (multi-stage: pnpm build → python:3.13-slim, port 7860)
✅ 環境変数による設定 (`app/config.py`, `backend/.env.example`) — 未設定なら従来どおりAerのみで動作
✅ Hugging Face Docker Space への1コマンド投入 (`deploy/hf_space.py`, Secret登録込み)
✅ docs/DEPLOY.md — 構成図・環境変数表・QPU枠の見積もり・Render代替案
