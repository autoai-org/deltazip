python cli/compress.py --target-model dmayhem93/pythia-125M-Summarization-sft --base-model EleutherAI/pythia-125m-deduped --dataset .cache/datasets/negotiation_strategy_detection.train.jsonl --bits 8 --sparsity 0.5 --lossless gdeflate --delta subtract --outdir .cache/compressed_models/p125m_gsd_133 --group-size 128