"""
(c) 2026 eastlakefish.com
This script implements an efficient ImageNet dataset based on sharded data.
(Parallel Training Version)

Assume the dataset has the following structure:
```text
ROOT
  ├── train
  │     └── shard_0.tar, ...
  │           └── <label>.<filename>.<suffix>
  └── val
        └── shard_0.tar, ...
              └── <label>.<filename>.<suffix>
```

This code is open-source under GNU GPL v2.0.
See https://eastlakefish.com/license.html.

"""

from __future__ import annotations

import os
from logging import warning

import torch
from torch import Tensor
from torch import distributed as dist
from torch.cuda import nccl as cuda_nccl

from efficient_imagenet import EfficientImageNet, split_list, benchmark_dataloader


def split_list_safe(l: list, n: int) -> list:
    return split_list(l[:len(l) // n * n], n)


class EfficientImageNetDDP(EfficientImageNet):
    def __init__(self, *args, **kwargs) -> None:
        if dist.is_initialized():
            self.world_size = dist.get_world_size()
        else:  # fallback
            self.world_size = 1
        
        self.enable_ddp = self.world_size > 1
        if not self.enable_ddp:
            warning("Using EfficientImageNetDDP with world_size=1.")
        
        super().__init__(*args, **kwargs)
        
        # assign batches
        if self.enable_ddp:
            self.imgs = {split: split_list_safe(imgs, self.world_size) for split, imgs in self.imgs.items()}
            
    @staticmethod
    def availability_check() -> None:
        print("Checking device availability...")
        print(f"cuda_is_available: {torch.cuda.is_available()}\n" + "-" * 50)
        availability = {
            "distribute_is_available": dist.is_available(),
            "nccl_is_available": dist.is_nccl_available(),
            "cuda_nccl_is_available": torch.cuda.is_available() and cuda_nccl.is_available(torch.randn(1).cuda()),
        }
        for entry, status in availability.items():
            print(f"{entry}: {status}")
        if not all(availability.values()):
            print("Availability check failed.")
            exit(1)
        
    @property
    def _ddp_batch(self) -> list[dict]:
        return self.imgs[self.split][dist.get_rank()] if self.enable_ddp else self.imgs[self.split]
        
    def __getitem__(self, item: int) -> tuple[Tensor, Tensor]:
        return self._process_getitem(self._ddp_batch, item, self.decode_mode)
    
    def __len__(self) -> int:
        return len(self._ddp_batch)


if __name__ == "__main__":
    # for debug only
    # when running with torchrun, the environmental variables
    # are set automatically
    
    import argparse
    import sys
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--world-size", type=int, default=1)
    parser.add_argument("-r", "--rank", type=int, default=0)
    args = parser.parse_args()
    
    if args.world_size > 1:
        os.environ['MASTER_ADDR'] = 'localhost'
        os.environ['MASTER_PORT'] = '12355'
        
        EfficientImageNetDDP.availability_check()
        
        backend = "gloo" if sys.platform.lower() == "windows" else "nccl"
        dist.init_process_group(backend=backend, rank=args.rank, world_size=args.world_size)
    
    try:
        dataset = EfficientImageNetDDP(root=r"F:\ResearchProjects\Datasets\ImageNet\compressed_batch=10000")
        benchmark_dataloader(dataset.train)
    finally:
        if dist.is_initialized():
            dist.destroy_process_group()
    