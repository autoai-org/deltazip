import math
import time
import torch
import transformers
import torch.nn as nn
from loguru import logger
from quant import quantize

DEBUG = False

torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

def hard_threshold(x, fraction_of_zero=0.1):
    if fraction_of_zero == 0:
        return x, None
    # randomly set random_sparsification of the weights to zero
    y, _ = torch.sort(x.view(-1).abs().clone())
    num_params = torch.numel(x)
    thresh_index = int(num_params * fraction_of_zero)
    threshold = y[thresh_index]
    mask = x.abs().clone().gt(threshold).type(torch.cuda.HalfTensor)
    return mask * x, mask

class GPTQ:
    def __init__(self, layer):
        self.layer = layer
        self.original_weight = layer.weight.data.clone()
        self.dev = self.layer.weight.device
        W = layer.weight.data.clone()
        if isinstance(self.layer, nn.Conv2d):
            W = W.flatten(1)
        if isinstance(self.layer, transformers.Conv1D):
            W = W.t()
        self.rows = W.shape[0]
        self.columns = W.shape[1]
        self.H = torch.zeros((self.columns, self.columns), device=self.dev)
        self.nsamples = 0

    def add_batch(self, inp, out):
        self.inp1 = inp
        self.out1 = out
        if len(inp.shape) == 2:
            inp = inp.unsqueeze(0)
        tmp = inp.shape[0]
        if isinstance(self.layer, nn.Linear):
            if len(inp.shape) == 3:
                inp = inp.reshape((-1, inp.shape[-1]))
            inp = inp.t()
        self.H *= self.nsamples / (self.nsamples + tmp)
        self.nsamples += tmp
        # inp = inp.float()
        inp = math.sqrt(2 / self.nsamples) * inp.float()
        # self.H += 2 / self.nsamples * inp.matmul(inp.t())
        self.H += inp.matmul(inp.t())

    def fasterquant(
        self, blocksize=128, percdamp=.01, groupsize=-1, actorder=False, write=True, sparsity=None
    ):
        W = self.layer.weight.data.clone()
        if isinstance(self.layer, nn.Conv2d):
            W = W.flatten(1)
        if isinstance(self.layer, transformers.Conv1D):
            W = W.t()
        W = W.float()

        tick = time.time()

        if not self.quantizer.ready():
            self.quantizer.find_params(W, weight=True)

        H = self.H
        if write:
            del self.H
        dead = torch.diag(H) == 0
        H[dead, dead] = 1
        W[:, dead] = 0

        if actorder:
            perm = torch.argsort(torch.diag(H), descending=True)
            W = W[:, perm]
            H = H[perm][:, perm]

        Losses = torch.zeros_like(W)
        Q = torch.zeros_like(W)

        damp = percdamp * torch.mean(torch.diag(H))
        diag = torch.arange(self.columns, device=self.dev)
        H[diag, diag] += damp
        H = torch.linalg.cholesky(H)
        H = torch.cholesky_inverse(H)
        H = torch.linalg.cholesky(H, upper=True)
        Hinv = H

        for i1 in range(0, self.columns, blocksize):
            i2 = min(i1 + blocksize, self.columns)
            count = i2 - i1

            W1 = W[:, i1:i2].clone()
            Q1 = torch.zeros_like(W1)
            Err1 = torch.zeros_like(W1)
            Losses1 = torch.zeros_like(W1)
            Hinv1 = Hinv[i1:i2, i1:i2]

            for i in range(count):
                w = W1[:, i]
                d = Hinv1[i, i]

                if groupsize != -1:
                    if (i1 + i) % groupsize == 0:
                        self.quantizer.find_params(W[:, (i1 + i):(i1 + i + groupsize)], weight=True)

                q = quantize(
                    w.unsqueeze(1), self.quantizer.scale, self.quantizer.zero, self.quantizer.maxq
                ).flatten()
                Q1[:, i] = q
                Losses1[:, i] = (w - q) ** 2 / d ** 2

                err1 = (w - q) / d
                W1[:, i:] -= err1.unsqueeze(1).matmul(Hinv1[i, i:].unsqueeze(0))
                Err1[:, i] = err1

            Q[:, i1:i2] = Q1
            Losses[:, i1:i2] = Losses1 / 2

            W[:, i2:] -= Err1.matmul(Hinv[i1:i2, i2:])

        torch.cuda.synchronize()
        if actorder:
            invperm = torch.argsort(perm)
            Q = Q[:, invperm]
        if isinstance(self.layer, transformers.Conv1D):
            Q = Q.t()
        new_weight = Q.reshape(self.layer.weight.shape).to(self.layer.weight.dtype)
        losses = {}
        mask = None
        if sparsity is None:
            sparsed_new_weight = new_weight
            losses[0] = torch.sum((self.inp1 @ (sparsed_new_weight.T) - self.out1) ** 2)
        else:
            for s_sity in sparsity:
                sparsed_new_weight, mask = hard_threshold(new_weight, fraction_of_zero=s_sity)
                print("new weight")
                print(self.inp1 @ (sparsed_new_weight.T))
                print("original weight")
                print(self.out1)
                if write:
                    logger.debug(f"HT with: sparsity={s_sity}")
                losses[s_sity] = torch.sum((self.inp1 @ (sparsed_new_weight.T) - self.out1) ** 2)
                print(losses)
        if write:
            self.layer.weight.data = sparsed_new_weight
        return losses, mask

    def free(self):
        if DEBUG:
            self.inp1 = None
            self.out1 = None
        self.H = None
        self.Losses = None
        self.Trace = None
        torch.cuda.empty_cache()