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
⏭ IBM Quantumバックエンド — 見送り (認証情報なしでは検証不能なため。QuantumBackend Protocolに実装を差すだけで追加可能, READMEに手順記載)

## Phase 6 — 仕上げ
✅ チュートリアル文言 (誤概念対策) — 初回自動表示 + ヘッダー「使い方」で再表示。5ステップで「Groverは答えを知らない」「候補を絞るのはあなた」「over-rotation」を伝える。localStorageで既読記憶、Esc/背景クリックで閉じる、reduced-motion対応
✅ README最終化 — 起動手順・辞書出典・アーキテクチャ図・チュートリアル節・UIレイアウト図を整備。Project Status を Phase 6 完了に更新
⏭ スクリーンショット — 実物撮影は見送り (README内テキストのUIレイアウト図で代替)
⏭ Docker — 見送り (DESIGN.md D7で「任意」。`git clone` → 手順通りで動くことは保証済み)
