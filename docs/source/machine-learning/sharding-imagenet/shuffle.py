"""
(c) 2026 eastlakefish.com
This script shuffles sharded ImageNet dataset.

This code is open-source under GNU GPL v2.0.
See https://eastlakefish.com/license.html.

"""

from __future__ import annotations

import multiprocessing
import random
import sys
import tarfile

from multiprocessing import Process, Queue
from pathlib import Path
from tqdm import tqdm
from typing import Callable


def split_list(lst: list, n: int) -> list[list]:
    return [lst[i * len(lst) // n : (i + 1) * len(lst) // n] for i in range(n)]


class ImageNetShuffle:
    def __init__(self, 
        root: Path, 
        compressed_dir: str,
        transform: Callable | None = None,
        num_workers: int = 8
    ) -> None:
        self.root = Path(root)
        self.compressed_dir = self.root / compressed_dir
        self.num_workers = num_workers
        self.transform = transform
        
        self.train_tar = self.root / "ILSVRC2012_img_train.tar"
        self.devkit_root = self.root / "ILSVRC2012_devkit_t12.tar.gz"
        
        self.val_gt = self.load_devkit(self.devkit_root)
        self.shard_paths = self.inspect_shards(self.compressed_dir)
        self.wnid2label = self._wnid2label()
        self.shard2worker, self.worker2shard = self._assign_shards()
        
        self.train_imgs = self._cache_imgs("train")
        self.val_imgs = self._cache_imgs("val")
    
    @staticmethod
    def load_devkit(path: Path) -> list[int]:
        with tarfile.open(path, "r:gz") as tar:
            tarinfo = tar.getmember("ILSVRC2012_devkit_t12/data/ILSVRC2012_validation_ground_truth.txt")
            return [int(line.strip()) for line in tar.extractfile(tarinfo).read().decode("utf-8").splitlines()]
        
    @staticmethod
    def inspect_shards(root: Path) -> dict:
        return {s: {shard_id: p for shard_id, p in enumerate(sorted(list((root / s).glob("shard_*.tar"))))} for s in ("train", "val")}
        
    @staticmethod
    def parse_wnid(filename: str) -> str:
        return filename.split(".")[0]
    
    def _wnid2label(self) -> dict:
        with tarfile.open(self.train_tar, "r") as tar:
            return {wnid: label for label, wnid in enumerate(sorted(
                mem.name.split(".")[0] for mem in tar.getmembers() if (mem.isfile() and mem.name.endswith(".tar"))
            ))}
    
    def _assign_shards(self) -> tuple[dict, dict]:
        shard2worker, worker2shard = ({s: {} for s in self.shard_paths.keys()} for _ in range(2))
        for s, v in self.shard_paths.items():
            batches = split_list(list(v.items()), self._num_workers(s))
            for worker_id, batch in enumerate(batches):
                for shard_id, _ in batch:
                    shard2worker[s][shard_id] = worker_id
                    worker2shard[s][worker_id] = worker2shard[s].get(worker_id, []) + [shard_id]
        return shard2worker, worker2shard
    
    def _num_workers(self, split: int) -> int:
        return min(self.num_workers, int(0.5 * multiprocessing.cpu_count()), len(self.shard_paths[split]))
    
    # general process
    @staticmethod
    def _process(job: Callable, in_queue: Queue | None, out_queue: Queue | None) -> None:
        while True:
            d = in_queue.get()
            if d is None:
                break
            try:
                out_queue.put(job(d))
            except:  # noqa: E722
                continue
            
    @staticmethod
    def _inspect_shard_images(shard_paths: list[tuple[int, Path]], out_queue: Queue) -> None:
        for shard_id, path in shard_paths:
            with tarfile.open(path, "r") as tar:
                for mem in tar.getmembers():
                    if mem.isfile() and mem.name.split(".")[-1].lower() in ("jpg", "jpeg"):
                        out_queue.put(f"{shard_id}/{mem.name}")
        out_queue.put(None)
    
    @staticmethod
    def _collect_shard_images(pbar: tqdm, in_queue: Queue, num_workers: int) -> list[str]:
        counter, images = 0, []
        while True:
            d = in_queue.get()
            if d is None:
                counter += 1
                if counter == num_workers:
                    break
                continue
            images.append(d)
            pbar.update()
        return images
    
    def _cache_imgs(self, split: str) -> list[str]:
        img_count = {
            "train": 1_281_167,
            "val": 50_000,
        }
        queue, num_workers = Queue(), self._num_workers(split)
        batches = split_list(list(self.shard_paths[split].items()), num_workers)
        inspectors = [Process(target=self._inspect_shard_images, kwargs={
            "shard_paths": batch,
            "out_queue": queue,
        }) for batch in batches]
        for ins in inspectors:
            ins.start()
        pbar = tqdm(total=img_count[split], desc=f"Caching {split}", file=sys.stdout)
        cache = self._collect_shard_images(pbar, queue, num_workers)
        print(f"Cache for split {split} in memory: {sys.getsizeof(cache) / (1024**2):.2f}MB")
        return cache
    
    def shuffle(self) -> list[str]:
        random.shuffle(self.train_imgs)
        return self.train_imgs
        

if __name__ == "__main__":
    loader = ImageNetShuffle(
        root=r"F:\ResearchProjects\Datasets\ImageNet",
        compressed_dir=r"compressed_batch=10000",
        num_workers=4,
    )
    
    print(loader.train_imgs[:10])
    print(loader.val_imgs[:10])
