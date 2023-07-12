import copy
import torch
import argparse
from loguru import logger
from transformers import AutoModelForCausalLM
from safetensors.torch import save_file

def benchmark_nvcomp(args):
    print(args)
    tensors = {}
    if args.base_model is not None:
        base_model = AutoModelForCausalLM.from_pretrained(args.base_model)
        target_model = AutoModelForCausalLM.from_pretrained(args.model)
        # base_model.half()
        # target_model.half()
        original_target_model = copy.deepcopy(target_model)
        for name1, param1 in base_model.named_parameters():
            target_model.state_dict()[name1] -= param1
        base_model.requires_grad_(False)
        target_model.requires_grad_(False)
        with torch.no_grad():
            for name1, param1 in target_model.named_parameters():
                target_param = original_target_model.state_dict()[name1]
                delta_param = target_model.state_dict()[name1]
                assert torch.allclose(target_param, base_model.state_dict()[name1]+delta_param)
    else:
        target_model = AutoModelForCausalLM.from_pretrained(args.model)
        # target_model.half()
    tensors = {}
    for name1, param1 in target_model.named_parameters():
        tensors[name1] = param1
    print("Saving model")
    save_file(tensors, args.output)
    print("Done")

if __name__=="__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--base-model", type=str, required=False, default=None)
    argparser.add_argument("--model", type=str, required=True)
    argparser.add_argument("--output", type=str, required=True)
    args = argparser.parse_args()
    benchmark_nvcomp(args)