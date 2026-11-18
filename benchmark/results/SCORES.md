# PokeVision scores

337 questions in 10 categories; one 480x432 screenshot a question, no history. Accuracy %, every item counts (no answer = wrong). Macro = mean of the 10 category accuracies.

| model | macro | reading | graphics | scene | correct/all | text | cursor | enemy_name | enemy_level | player_hp | enemy_hp_bar | facing | npc_count | walkable | place |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | **98.3** | 99.4 | 99.1 | 94.3 | 331/337 | 97 | 100 | 100 | 100 | 100 | 100 | 97 | 100 | 100 | 89 |
| claude-opus-5-5-high | **96.6** | 100.0 | 92.6 | 94.3 | 325/337 | 100 | 100 | 100 | 100 | 100 | 100 | 78 | 100 | 100 | 89 |
| claude-opus-5-5 | **95.5** | 100.0 | 91.7 | 90.1 | 321/337 | 100 | 100 | 100 | 100 | 100 | 100 | 75 | 100 | 94 | 86 |
| Kimi-K3.1-Pro-run2 | **92.3** | 99.4 | 82.1 | 90.0 | 310/337 | 97 | 100 | 100 | 100 | 100 | 91 | 56 | 100 | 97 | 83 |
| Kimi-K3.1-Pro | **91.4** | 100.0 | 79.1 | 88.6 | 307/337 | 100 | 100 | 100 | 100 | 100 | 84 | 56 | 97 | 97 | 80 |
| Qwen3.8-Flash-Next | **82.6** | 97.8 | 68.3 | 66.1 | 276/337 | 89 | 100 | 100 | 100 | 100 | 69 | 47 | 89 | 75 | 57 |
| Qwen3.8-Flash-Next-run2 | **82.0** | 97.7 | 63.8 | 70.3 | 274/337 | 92 | 100 | 100 | 97 | 100 | 72 | 36 | 83 | 81 | 60 |
| GLM-5.3-Flash | **77.3** | 90.7 | 64.5 | 63.4 | 259/337 | 86 | 97 | 100 | 73 | 97 | 66 | 39 | 89 | 64 | 63 |
| openrouter_tencent_hy4-flash | **66.2** | 80.0 | 44.3 | 64.6 | 222/337 | 69 | 97 | 97 | 50 | 87 | 47 | 42 | 44 | 81 | 49 |
| GLM-5.3-blind | **11.1** | 3.3 | 13.5 | 26.6 | 38/337 | 0 | 0 | 7 | 10 | 0 | 16 | 22 | 3 | 36 | 17 |
| *majority-answer baseline* | 21.6 | | | | | 3 | 6 | 27 | 27 | 3 | 31 | 25 | 25 | 50 | 20 |

## Per category: k/n, 95% Wilson interval, invalid / no-final / errors, median seconds and output tokens

### text (n=36)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok | mean CER |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 35/36 | 97.2 | 86-100 | 0 | 0 | 0 | 10.2 | None | 0.001 |
| claude-opus-5-5-high | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 2.3 | None | 0.000 |
| claude-opus-5-5 | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 1.5 | None | 0.000 |
| Kimi-K3.1-Pro-run2 | 35/36 | 97.2 | 86-100 | 0 | 0 | 0 | 4.0 | 216.0 | 0.002 |
| Kimi-K3.1-Pro | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 2.4 | 188.0 | 0.000 |
| Qwen3.8-Flash-Next | 32/36 | 88.9 | 75-96 | 0 | 0 | 0 | 2.6 | 76.5 | 0.005 |
| Qwen3.8-Flash-Next-run2 | 33/36 | 91.7 | 78-97 | 0 | 0 | 0 | 2.0 | 77.0 | 0.004 |
| GLM-5.3-Flash | 31/36 | 86.1 | 71-94 | 1 | 1 | 0 | 8.6 | 98.0 | 0.033 |
| openrouter_tencent_hy4-flash | 25/36 | 69.4 | 53-82 | 0 | 0 | 0 | 3.4 | None | 0.013 |
| GLM-5.3-blind | 0/36 | 0.0 | 0-10 | 7 | 1 | 0 | 18.9 | 391.5 | 0.996 |

### cursor (n=36)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 7.9 | None |
| claude-opus-5-5-high | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 1.2 | None |
| claude-opus-5-5 | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 1.4 | None |
| Kimi-K3.1-Pro-run2 | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 2.1 | 88.0 |
| Kimi-K3.1-Pro | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 0.9 | 82.5 |
| Qwen3.8-Flash-Next | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 2.0 | 85.0 |
| Qwen3.8-Flash-Next-run2 | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 1.8 | 87.0 |
| GLM-5.3-Flash | 35/36 | 97.2 | 86-100 | 0 | 0 | 0 | 8.5 | 48.5 |
| openrouter_tencent_hy4-flash | 35/36 | 97.2 | 86-100 | 0 | 0 | 0 | 3.1 | None |
| GLM-5.3-blind | 0/36 | 0.0 | 0-10 | 5 | 0 | 0 | 12.6 | 469.5 |

### enemy_name (n=30)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 8.9 | None |
| claude-opus-5-5-high | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.2 | None |
| claude-opus-5-5 | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.3 | None |
| Kimi-K3.1-Pro-run2 | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.1 | 61.5 |
| Kimi-K3.1-Pro | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 0.7 | 60.5 |
| Qwen3.8-Flash-Next | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 2.4 | 74.5 |
| Qwen3.8-Flash-Next-run2 | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.5 | 76.0 |
| GLM-5.3-Flash | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 8.2 | 63.0 |
| openrouter_tencent_hy4-flash | 29/30 | 96.7 | 83-99 | 0 | 0 | 0 | 3.1 | None |
| GLM-5.3-blind | 2/30 | 6.7 | 2-21 | 3 | 0 | 0 | 15.5 | 612.0 |

### enemy_level (n=30)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 8.8 | None |
| claude-opus-5-5-high | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.2 | None |
| claude-opus-5-5 | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.3 | None |
| Kimi-K3.1-Pro-run2 | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 0.9 | 70.5 |
| Kimi-K3.1-Pro | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 0.8 | 72.0 |
| Qwen3.8-Flash-Next | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 4.2 | 66.0 |
| Qwen3.8-Flash-Next-run2 | 29/30 | 96.7 | 83-99 | 0 | 0 | 0 | 1.5 | 71.5 |
| GLM-5.3-Flash | 22/30 | 73.3 | 56-86 | 3 | 3 | 0 | 5.8 | 72.5 |
| openrouter_tencent_hy4-flash | 15/30 | 50.0 | 33-67 | 0 | 0 | 0 | 3.2 | None |
| GLM-5.3-blind | 3/30 | 10.0 | 3-26 | 14 | 2 | 0 | 11.6 | 442.5 |

### player_hp (n=30)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 7.3 | None |
| claude-opus-5-5-high | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.2 | None |
| claude-opus-5-5 | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.3 | None |
| Kimi-K3.1-Pro-run2 | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.3 | 80.5 |
| Kimi-K3.1-Pro | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 0.7 | 76.5 |
| Qwen3.8-Flash-Next | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 2.5 | 97.0 |
| Qwen3.8-Flash-Next-run2 | 30/30 | 100.0 | 89-100 | 0 | 0 | 0 | 1.7 | 95.5 |
| GLM-5.3-Flash | 29/30 | 96.7 | 83-99 | 1 | 1 | 0 | 3.3 | 81.0 |
| openrouter_tencent_hy4-flash | 26/30 | 86.7 | 70-95 | 0 | 0 | 0 | 2.9 | None |
| GLM-5.3-blind | 0/30 | 0.0 | 0-11 | 5 | 0 | 0 | 12.3 | 467.5 |

### enemy_hp_bar (n=32)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 32/32 | 100.0 | 89-100 | 0 | 0 | 0 | 8.8 | None |
| claude-opus-5-5-high | 32/32 | 100.0 | 89-100 | 0 | 0 | 0 | 2.8 | None |
| claude-opus-5-5 | 32/32 | 100.0 | 89-100 | 0 | 0 | 0 | 1.7 | None |
| Kimi-K3.1-Pro-run2 | 29/32 | 90.6 | 76-97 | 0 | 0 | 0 | 7.1 | 372.0 |
| Kimi-K3.1-Pro | 27/32 | 84.4 | 68-93 | 0 | 0 | 0 | 6.5 | 419.0 |
| Qwen3.8-Flash-Next | 22/32 | 68.8 | 51-82 | 0 | 0 | 0 | 4.6 | 401.0 |
| Qwen3.8-Flash-Next-run2 | 23/32 | 71.9 | 55-84 | 1 | 1 | 0 | 3.4 | 349.5 |
| GLM-5.3-Flash | 21/32 | 65.6 | 48-80 | 0 | 0 | 0 | 4.9 | 231.0 |
| openrouter_tencent_hy4-flash | 15/32 | 46.9 | 31-64 | 0 | 0 | 0 | 3.1 | None |
| GLM-5.3-blind | 5/32 | 15.6 | 7-32 | 1 | 0 | 0 | 12.8 | 519.5 |

### facing (n=36)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 35/36 | 97.2 | 86-100 | 0 | 0 | 0 | 7.8 | None |
| claude-opus-5-5-high | 28/36 | 77.8 | 62-88 | 0 | 0 | 0 | 4.4 | None |
| claude-opus-5-5 | 27/36 | 75.0 | 59-86 | 0 | 0 | 0 | 3.1 | None |
| Kimi-K3.1-Pro-run2 | 20/36 | 55.6 | 40-70 | 0 | 0 | 0 | 18.1 | 1014.5 |
| Kimi-K3.1-Pro | 20/36 | 55.6 | 40-70 | 0 | 0 | 0 | 15.0 | 1158.5 |
| Qwen3.8-Flash-Next | 17/36 | 47.2 | 32-63 | 0 | 0 | 0 | 44.0 | 4286.0 |
| Qwen3.8-Flash-Next-run2 | 13/36 | 36.1 | 22-52 | 0 | 0 | 0 | 39.2 | 4000.5 |
| GLM-5.3-Flash | 14/36 | 38.9 | 25-55 | 2 | 2 | 0 | 10.3 | 387.0 |
| openrouter_tencent_hy4-flash | 15/36 | 41.7 | 27-58 | 0 | 0 | 0 | 3.4 | None |
| GLM-5.3-blind | 8/36 | 22.2 | 12-38 | 5 | 2 | 0 | 15.4 | 583.5 |

### npc_count (n=36)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 8.0 | None |
| claude-opus-5-5-high | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 3.0 | None |
| claude-opus-5-5 | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 1.8 | None |
| Kimi-K3.1-Pro-run2 | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 3.6 | 211.5 |
| Kimi-K3.1-Pro | 35/36 | 97.2 | 86-100 | 0 | 0 | 0 | 3.2 | 263.5 |
| Qwen3.8-Flash-Next | 32/36 | 88.9 | 75-96 | 0 | 0 | 0 | 4.1 | 345.5 |
| Qwen3.8-Flash-Next-run2 | 30/36 | 83.3 | 68-92 | 1 | 1 | 0 | 4.5 | 409.0 |
| GLM-5.3-Flash | 32/36 | 88.9 | 75-96 | 2 | 1 | 0 | 6.6 | 228.0 |
| openrouter_tencent_hy4-flash | 16/36 | 44.4 | 30-60 | 0 | 0 | 0 | 3.1 | None |
| GLM-5.3-blind | 1/36 | 2.8 | 0-14 | 15 | 2 | 0 | 14.5 | 565.0 |

### walkable (n=36)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 9.8 | None |
| claude-opus-5-5-high | 36/36 | 100.0 | 90-100 | 0 | 0 | 0 | 5.6 | None |
| claude-opus-5-5 | 34/36 | 94.4 | 82-98 | 0 | 0 | 0 | 3.5 | None |
| Kimi-K3.1-Pro-run2 | 35/36 | 97.2 | 86-100 | 0 | 0 | 0 | 11.7 | 770.0 |
| Kimi-K3.1-Pro | 35/36 | 97.2 | 86-100 | 0 | 0 | 0 | 10.8 | 661.5 |
| Qwen3.8-Flash-Next | 27/36 | 75.0 | 59-86 | 0 | 0 | 0 | 16.1 | 1411.5 |
| Qwen3.8-Flash-Next-run2 | 29/36 | 80.6 | 65-90 | 0 | 0 | 0 | 11.9 | 1280.5 |
| GLM-5.3-Flash | 23/36 | 63.9 | 48-78 | 12 | 12 | 0 | 97.9 | 5430.0 |
| openrouter_tencent_hy4-flash | 29/36 | 80.6 | 65-90 | 0 | 0 | 0 | 3.4 | None |
| GLM-5.3-blind | 13/36 | 36.1 | 22-52 | 7 | 1 | 0 | 15.2 | 559.0 |

### place (n=35)

| model | k/n | acc % | 95% CI | invalid | no-final | errors | median s | median out tok |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| openai-codex_gpt-6.2-astra | 31/35 | 88.6 | 74-95 | 0 | 0 | 0 | 8.1 | None |
| claude-opus-5-5-high | 31/35 | 88.6 | 74-95 | 0 | 0 | 0 | 3.0 | None |
| claude-opus-5-5 | 30/35 | 85.7 | 71-94 | 0 | 0 | 0 | 1.5 | None |
| Kimi-K3.1-Pro-run2 | 29/35 | 82.9 | 67-92 | 0 | 0 | 0 | 7.5 | 445 |
| Kimi-K3.1-Pro | 28/35 | 80.0 | 64-90 | 1 | 1 | 0 | 3.1 | 298 |
| Qwen3.8-Flash-Next | 20/35 | 57.1 | 41-72 | 2 | 2 | 0 | 7.1 | 610 |
| Qwen3.8-Flash-Next-run2 | 21/35 | 60.0 | 44-74 | 2 | 2 | 0 | 5.8 | 539 |
| GLM-5.3-Flash | 22/35 | 62.9 | 46-77 | 4 | 4 | 0 | 6.4 | 275 |
| openrouter_tencent_hy4-flash | 17/35 | 48.6 | 33-64 | 0 | 0 | 0 | 3.5 | None |
| GLM-5.3-blind | 6/35 | 17.1 | 8-33 | 3 | 1 | 0 | 11.0 | 404 |

