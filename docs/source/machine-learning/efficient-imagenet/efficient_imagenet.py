"""
(c) 2026 eastlakefish.com
This script implements an efficient ImageNet dataset based on sharded data.

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

import multiprocessing as mp
import sys
import tarfile
import time

from functools import partial
from pathlib import Path
from tqdm import tqdm
from typing import Iterator, Sequence

import torch
from torch import Tensor
from torch.utils.data import Dataset, DataLoader

from torchvision.io import decode_image

DEFAULT_IMAGE_SUFFIXES = ("jpg", "jpeg", "JPEG", "png", "PNG")
tqdm = partial(tqdm, file=sys.stdout)


def split_list(lst: list, n: int) -> list[list]:
    return [lst[i * len(lst) // n : (i + 1) * len(lst) // n] for i in range(n)]


class EfficientImageNet(Dataset):
    def __init__(self,
        root: str | Path,
        *,
        num_workers: int = 8,
        img_suffixes: Sequence[str] = DEFAULT_IMAGE_SUFFIXES,
        decode_mode: str = "RGB",
    ) -> None:
        super().__init__()
        self.root = Path(root)
        self.shards = self.list_shards(self.root)
        self.num_workers = min(num_workers, mp.cpu_count())
        self.decode_mode = decode_mode
        
        self.imgs = self.inspect_imgs(self.shards, self.num_workers, img_suffixes)
        self.__train__ = True
    
    @staticmethod
    def list_shards(root: str | Path) -> None:
        root = Path(root)
        return {split: list((root / split).glob("shard_*.tar")) for split in ("train", "val")}
    
    @staticmethod
    def inspect_worker(shard_list: list[Path], img_suffixes: Sequence[str], output_queue: mp.Queue) -> None:
        for shard in shard_list:
            try:
                with tarfile.open(shard, "r|") as tar:
                    while mem := tar.next():
                        if mem.isfile():
                            name_frags = mem.name.split(".")
                            if name_frags[-1] in img_suffixes:
                                output_queue.put({
                                    "shard": shard,
                                    "label": name_frags[0],
                                    "offset": mem.offset_data,
                                    "size": mem.size,
                                })
            finally:
                output_queue.put(None)

    @classmethod
    def inspect_imgs(cls,
        shards: dict[str, list[Path]],
        num_workers: int,
        img_suffixes: Sequence[str] = DEFAULT_IMAGE_SUFFIXES,
    ) -> None:
        results = {}
        for split, shard_list in shards.items():
            results[split], total = [], len(shard_list)
            num_workers = min(num_workers, len(shard_list))
            pbar = tqdm(total=total, desc=f"Caching {split}")
            shard_batches = split_list(shard_list, num_workers)
            queue = mp.Queue(maxsize=20 * num_workers)
            
            workers = [mp.Process(target=cls.inspect_worker, args=(batch, img_suffixes, queue)) for batch in shard_batches]
            for w in workers:
                w.start()
            
            finished = 0
            while finished < total:
                flag = queue.get()
                if flag is None:
                    finished += 1
                    pbar.update()
                else:
                    results[split].append(flag)
                
            for w in workers:
                w.join()
        
        return results
    
    @property
    def train(self) -> EfficientImageNet:
        self.__train__ = True
        return self
    
    @property
    def val(self) -> EfficientImageNet:
        self.__train__ = False
        return self
    
    @property
    def split(self) -> str:
        return "train" if self.__train__ else "val"
    
    def __getitem__(self, item: int) -> tuple[Tensor, Tensor]:
        # per worker
        # world_size=1
        if item >= len(self.imgs[self.split]):
            raise IndexError(f"Index {item} out of range.")
        img_meta = self.imgs[self.split][item]
        label = torch.as_tensor(int(img_meta["label"]), dtype=torch.long)
        with open(img_meta["shard"], "rb") as f:
            f.seek(img_meta["offset"])
            img_bytes = f.read(img_meta["size"])
        buf = torch.frombuffer(img_bytes, dtype=torch.uint8)
        img = decode_image(buf, mode=self.decode_mode)
        return img, label
    
    def __len__(self) -> int:
        return len(self.imgs[self.split])
    
    def __iter__(self) -> Iterator[tuple[Tensor, Tensor]]:  # for debug
        index = 0
        while True:
            try:
                yield self[index]
            except IndexError:
                break
            index += 1
            

# ------ benchmark ------

def benchmark_dataloader(
    dataset,
    batch_size: int = 256,
    num_workers: int = 8,
    warmup_batches: int = 10,
    benchmark_batches: int = 500,
) -> None:
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        persistent_workers=(num_workers > 0),
        drop_last=True,
    )

    it = iter(loader)

    # warmup
    for _ in tqdm(range(warmup_batches), desc="Warmup"):
        next(it)

    # benchmark
    t0 = time.perf_counter()
    num_samples = 0

    for _ in tqdm(range(benchmark_batches), desc="Benchmark"):
        _, y = next(it)
        num_samples += len(y)

    t1 = time.perf_counter()

    elapsed = t1 - t0

    print(f"Batch size:        {batch_size}")
    print(f"Num workers:       {num_workers}")
    print(f"Warmup batches:    {warmup_batches}")
    print(f"Benchmark batches: {benchmark_batches}")
    print(f"Elapsed:           {elapsed:.3f} s")
    print(f"Samples:           {num_samples}")
    print(f"Samples/sec:       {num_samples / elapsed:.2f}")
    print(f"Batches/sec:       {benchmark_batches / elapsed:.2f}")

    return {
        "batch_size": batch_size,
        "num_workers": num_workers,
        "samples_per_sec": num_samples / elapsed,
        "batches_per_sec": benchmark_batches / elapsed,
    }
    
    
if __name__ == "__main__":
    dataset = EfficientImageNet(root="./imagenet12")
    benchmark_dataloader(dataset.train)