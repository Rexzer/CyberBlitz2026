#!/usr/bin/env python3
"""CYBERBLITZ 2026 "ragebait" — recover a LoRA backdoor trigger by greedy search.

The handout is a LoRA adapter for TinyLlama-1.1B-Chat plus a 390-word vocab.json
(a candidate list, not a real tokenizer vocab). Generating and hoping to see the
flag does not work; instead OPTIMISE THE INPUT FOR THE KNOWN OUTPUT FORMAT:

    objective = CE( model(chat(trigger)) -> "CYBLTZ2026{" )

then coordinate-descent each trigger position over the 390 candidates.
Converges to "give gg" in ~2,300 forward passes.

Setup:
    python3 -m venv /opt/ml-venv
    /opt/ml-venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
    /opt/ml-venv/bin/pip install transformers peft accelerate huggingface_hub
    # base model (~2.2GB); hf-mirror.com is far faster than rate-limited HF
"""
import json
import sys

import torch
import torch.nn.functional as F
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ADAPTER = sys.argv[1] if len(sys.argv) > 1 else "."
BASE = sys.argv[2] if len(sys.argv) > 2 else "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
TARGET = "CYBLTZ2026{"

torch.set_num_threads(8)
tok = AutoTokenizer.from_pretrained(ADAPTER)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
tok.padding_side = "left"
model = PeftModel.from_pretrained(
    AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float32), ADAPTER).eval()

VOCAB = [w["word"] for w in json.load(open(f"{ADAPTER}/vocab.json"))]
TGT_LEN = len(tok(TARGET, add_special_tokens=False)["input_ids"])


def chat(user):
    return f"<|system|>\n</s>\n<|user|>\n{user}</s>\n<|assistant|>\n"


def batch_loss(triggers):
    """mean CE of TARGET given each trigger (left-padded, so target is the tail)"""
    enc = tok([chat(t) + TARGET for t in triggers],
              return_tensors="pt", padding=True, add_special_tokens=True)
    with torch.no_grad():
        logits = model(**enc).logits
    L = enc["input_ids"].shape[1]
    pred = logits[:, L - TGT_LEN - 1:L - 1, :]
    gold = enc["input_ids"][:, L - TGT_LEN:L]
    lp = F.log_softmax(pred, dim=-1)
    return (-lp.gather(2, gold.unsqueeze(-1)).squeeze(-1)).mean(dim=1)


def search(length, passes=3, batch=64):
    trig, best = ["the"] * length, float("inf")
    for _ in range(passes):
        improved = False
        for pos in range(length):
            losses = []
            for i in range(0, len(VOCAB), batch):
                cand = VOCAB[i:i + batch]
                losses.append(batch_loss(
                    [" ".join(trig[:pos] + [w] + trig[pos + 1:]) for w in cand]))
            losses = torch.cat(losses)
            k = int(losses.argmin())
            if float(losses[k]) < best - 1e-4:
                best, trig[pos], improved = float(losses[k]), VOCAB[k], True
            print(f"  L={length} pos={pos} best={VOCAB[k]!r} "
                  f"loss={best:.4f} trigger={' '.join(trig)!r}")
        if not improved:
            break
    return best, " ".join(trig)


def generate(prompt, n=80):
    enc = tok(chat(prompt), return_tensors="pt", add_special_tokens=True)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=n, do_sample=False,
                             pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)


if __name__ == "__main__":
    results = [search(n) for n in (1, 2, 3)]
    results.sort()
    best_loss, trigger = results[0]
    print(f"\nBEST trigger={trigger!r} loss={best_loss:.4f}")
    print("GENERATION:", generate(trigger))
