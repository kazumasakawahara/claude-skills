# claude-skills

Claude 用の自作 Agent Skills を 4 本、公開しています。考える道具が 3 本（「決める」「調べる」「AI の完了報告を疑う」の 3 つの場面に 1 本ずつ）と、図を描く道具が 1 本です。日本語で書かれており、Claude の応答も日本語になります。

| スキル | 一行で言うと | 使う場面 | 使わない場面 |
|---|---|---|---|
| **deliberation-sim** | 決める道具。課題から賛成・反対・折衷・不在の当事者・裁定者の人格を生成し、確信度の変化を追跡しながら議論させて結論を導く熟議シミュレータ | 「やるべきか」「A か B か」「反対意見も潰しておきたい」「会議で結論を出す必要がある」 | 単なる情報質問、選択肢が 1 つしかない場面、決定済みで実行手順だけが要る場面、**決定権者が本人で本人の希望を聞くべき意思決定支援の場面**（本人の意思を人格の議論で代替してはいけない） |
| **hypothesis-arena** | 調べる道具。問いから相互排他的な仮説群と擁護者を生成し、文献予測と自滅条件を宣言させて競争させ、決着に最も効く判別読書課題を導く仮説競争シミュレータ | 「なぜ〜なのか」「どの説が有力か」「対立する学説を整理したい」「どの文献を読めば決着するか」 | 「〜すべきか」の意思決定（それは deliberation-sim）、単発の事実確認、文献の取得・変換そのもの |
| **acceptance-inspector** | AI の完了報告を疑う道具。「完了しました」と主張する成果物を、作業者と独立した立場で受入基準に照らして検品し、合否ではなく検証項目ごとの根拠と未検証の明示を返す | サブエージェントや Claude Code が「完了」「テスト通過」と報告した直後、本番反映の前、他者に成果物を渡す前 | 読んで論評する「レビュー」、作業者自身が自分の成果物を自己検品する用途（独立性が満たせない） |
| **genogram** | 図を描く道具。ある人物を中心にした家族関係の図（ジェノグラム）を、決まった記号で SVG に描く。図はスクリプトが描くので、同じ記録からは同じ図が出る。述べられていない親族関係は線にせず「記載なし」と注記する | 「ジェノグラムを描いて」「○○さんを中心にジェノグラムにして」。家族の構成（仮名・続柄・年齢・同居・婚姻や離婚など）を伝えて図にしたい、仮名（イニシャル）になっている資料の家族の図を作り直したい | **実名の入った資料を読み取らせる用途**（開くのは、仮名になっていると伝えられた資料だけ。伝えられていなければ、開かずに確かめる）、支援機関とのつながりの図（エコマップ）、相続関係の図、先祖をさかのぼる家系図、**夫婦の双方の実家を 1 枚に描く図**（描くのは一方の家系と、婚姻や事実婚で入った人。1 人の相手は 2 人まで） |

各スキルの詳しい手順は `skills/<name>/SKILL.md` と、同じフォルダの `PROTOCOL.md`・`reference/`・`examples/`・`templates/` にあります。acceptance-inspector には人間向けの手順書 `README.md`（作業会話と検品会話の分け方と、そのまま貼れるプロンプト）があります。genogram は `scripts/`（図を描くスクリプト。Python 3.9 以上で動き、追加の導入は要りません）と `examples/`（記録の見本）を持ちます。

## 入れ方（claude.ai / Claude Desktop）

**カスタムスキルの利用には Pro 以上のプランが必要です**（Free では設定項目が出ません）。

1. [Releases](https://github.com/kazumasakawahara/claude-skills/releases) から使いたいスキルの ZIP（`deliberation-sim.zip` 等）をダウンロードする
2. claude.ai の **設定 → カスタマイズ → スキル** を開く
3. **アップロード** を押し、ダウンロードした ZIP を選ぶ
4. 新しい会話を始めて、上の表の「使う場面」の言い方で頼む。スキルは自動で選ばれます（選ばれないときは「deliberation-sim を使って」のようにスキル名を言えば起動します）

ZIP は 1 スキル 1 本です。複数使うなら、その数だけアップロードしてください。更新するときは同じ手順で置き換えます。

## 入れ方（Claude Code）

```
/plugin marketplace add kazumasakawahara/claude-skills
/plugin install deliberation-sim@kawahara-skills
/plugin install hypothesis-arena@kawahara-skills
/plugin install acceptance-inspector@kawahara-skills
/plugin install genogram@kawahara-skills
```

marketplace 名は `kawahara-skills` です。プラグイン名はスキル名と同じです。

## 環境固有の設定と `local.md.example`

考える道具の 3 本（deliberation-sim・hypothesis-arena・acceptance-inspector）は、既定は **claude.ai だけで動く形**になっています。台帳や報告はダウンロードできる Markdown ファイルとして返し、立論は 1 つの会話で順に行い、継続の観測点は本文に期日を書いて人間に渡します。

この 3 本の `local.md.example` は、**Claude Code でサブエージェント並列や期日管理ツールとの連携などの拡張を使う人向け**の設定例です。スキルと同じディレクトリに `local.md` という名前で置くと、SKILL.md の「環境固有の設定」節の既定を上書きします。**claude.ai だけで使う場合は無視してかまいません。** genogram の `local.md.example` は、相談資料を点検してから扱う別のスキルや手順がある環境で、譲る相手を書くための例です。無ければ要りません。

## 個人の情報を扱うとき

個人の情報を入れて使う場合は各自の責任でお願いします。台帳・報告ファイルに実名を残さないことを勧めます（イニシャルや役割名に置き換える）。genogram は、図に出る名前を仮名・イニシャル・続柄にする決まりで、実名を記録に写しません。資料から作り直せるのは、仮名になっていると伝えた資料だけです。資料を添付すると、その中身は図を描く前に Claude に渡ります。実名の入った資料は添付しないでください。家族関係はそれだけで人を特定できることがあるので、図を渡す相手と保管の場所は各自で決めてください。

## 較正について

これらのスキルの当たり（deliberation-sim・hypothesis-arena の確信度の当たり、acceptance-inspector の欠陥検出率）は、まだ体系的に測っていません。acceptance-inspector には自己較正の手順（`references/canary.md`）を同梱していますが、著者の環境でも初回較正は未実施です。出力は判断材料であって判定ではない、と考えて使ってください。genogram は渡された記録のとおりに描くだけで、記録の正しさは確かめません。

## English

Four Japanese-language Agent Skills for Claude: **deliberation-sim** (a multi-persona deliberation simulator for "should we / which one" decisions), **hypothesis-arena** (a competing-hypotheses simulator for "why / which theory" questions that ends with a discriminating reading list), **acceptance-inspector** (an independent acceptance-inspection role that checks an AI's "done" claim against explicit criteria and reports evidence per item, including what it could not verify), and **genogram** (draws a family-relationship diagram centered on one person as an SVG with a deterministic script, and notes unstated kinship as "not recorded" instead of guessing it). Install on claude.ai / Claude Desktop (Pro or higher) by uploading a ZIP from [Releases](https://github.com/kazumasakawahara/claude-skills/releases) under Settings → Customize → Skills, or in Claude Code with `/plugin marketplace add kazumasakawahara/claude-skills` and `/plugin install <skill>@kawahara-skills`. The skills' prompts and outputs are in Japanese.

## 配布物の作り方（メンテナ向け）

```
scripts/check-parity.sh          # LEDGER 写しのずれ・local.md の混入・固有語の混入を検査（0 終了で合格）
                                 # 固有語検査は追跡外の scripts/local-terms.txt があるときだけ動く（保守者用。無ければ省略）
scripts/build-release.sh v0.1.0  # git archive から dist/<name>.zip を 4 本生成（追跡外ファイルは構造的に入らない）
```

## ライセンス

MIT License. 詳細は [LICENSE](LICENSE)。
