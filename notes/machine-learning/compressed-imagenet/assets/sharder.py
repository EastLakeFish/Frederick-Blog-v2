"""
(c) 2026 eastlakefish.com
This script implements a sharder for ImageNet dataset.

This code is open-source under GNU GPL v2.0.
See https://eastlakefish.com/license.html.

"""

from __future__ import annotations

import io
import tarfile

from multiprocessing import Queue, Process
from pathlib import Path
from PIL import Image
from tqdm import tqdm

IMAGE_SIZE = (224, 224)


def _process_img(img_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize(IMAGE_SIZE)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _worker_train(tar_queue: Queue, img_queue: Queue) -> None:
    while True:
        d = tar_queue.get()
        if d is None:
            break
        tar_name, tar_bytes = d
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r|") as tar:
            while member := tar.next():  # JPEG
                handler = tar.extractfile(member)
                if handler:
                    try:
                        img_queue.put((tar_name, member.name, _process_img(handler.read())))
                    except:
                        continue
                    
                    
def _worker_val(in_queue: Queue, out_queue: Queue) -> None:
    while True:
        d = in_queue.get()
        if d is None:
            break
        img_name, img_bytes = d
        try:
            out_queue.put((img_name, _process_img(img_bytes)))
        except:
            continue


def _collector(root: Path, batch_size: int, img_queue: Queue, total: int) -> None:
    def sharder(c: int) -> str:
        return root / f"shard_{c}.tar"
    
    root.mkdir(parents=True, exist_ok=True)
    
    shard_id, shard_counter = 0, 0
    pbar = tqdm(total=total, desc="Processing")
    target_tar = tarfile.open(sharder(shard_id), "w|")
    try:
        while True:
            d = img_queue.get()
            if d is None:
                break
            if len(d) == 3:  # train set
                label, filename, img_bytes = d
                file_info = tarfile.TarInfo(".".join((label, filename)))
            else:  # val set
                filename, img_bytes = d
                file_info = tarfile.TarInfo(filename)
            file_info.size = len(img_bytes)
            target_tar.addfile(file_info, io.BytesIO(img_bytes))
            if shard_counter == batch_size:
                shard_id += 1
                shard_counter = 0
                target_tar.close()
                target_tar = tarfile.open(sharder(shard_id), "w|")
            else:
                shard_counter += 1
            pbar.update()
    finally:
        target_tar.close()


class ImageNetSharder:
    img_total = {
        "train": 1_281_167,
        "val": 50_000,
    }
    
    def __init__(self,
        train_tar: str | Path,
        val_tar: str | Path,
        target: str | Path,
        batch_size: int = 10_000,
        num_workers: int = 8,
    ) -> None:
        self.paths = dict(train=Path(train_tar), val=Path(val_tar))
        self.target = Path(target)
        
        self.meta = self.inspect()
        self.batch_size = batch_size
        self.num_workers = num_workers
    
    def inspect(self) -> dict:
        def _inspect(tar) -> list:
            with tarfile.open(tar, "r") as tar:
                return list({
                    "name": member.name,  # for train set, these are tars
                    "size": member.size,
                    "offset": member.offset_data,
                } for member in tar.getmembers())
        return {k: _inspect(v) for k, v in self.paths.items()}
        
    def _assign(self, split: str, queue: Queue) -> bytes:
        with open(self.paths[split], "rb") as f:
            for meta in self.meta[split]:
                f.seek(meta["offset"])
                queue.put((
                    meta["name"].split(".")[0],  # remove suffix
                    f.read(meta["size"]),
                ))
        for _ in range(self.num_workers):
            queue.put(None)
    
    def start(self) -> None:
        # process train set
        tar_queue, img_queue = Queue(), Queue()
        workers = [Process(target=_worker_train, args=(tar_queue, img_queue)) for _ in range(self.num_workers)]
        collector = Process(target=_collector, args=(self.target / "train", self.batch_size, img_queue, self.img_total["train"]))
        for t in workers:
            t.start()
        collector.start()
        self._assign("train", tar_queue)
        for worker in workers:
            worker.join()
        img_queue.put(None)
        collector.join()
        
        # process val set
        in_queue, out_queue = Queue(), Queue()
        workers = [Process(target=_worker_val, args=(in_queue, out_queue)) for _ in range(self.num_workers)]
        collector = Process(target=_collector, args=(self.target / "val", self.batch_size, out_queue, self.img_total["val"]))
        for t in workers:
            t.start()
        collector.start()
        self._assign("val", in_queue)
        for worker in workers:
            worker.join()
        out_queue.put(None)
        collector.join()


if __name__ == "__main__":
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    parser.add_argument("root", nargs=1, type=str)
    parser.add_argument("-b", "--batch-size", type=int, default=10_000)
    parser.add_argument("-w", "--num-workers", type=int, default=8)
    args = parser.parse_args()
    
    root_path = Path(args.root[0])
    
    sharder = ImageNetSharder(
        train_tar=root_path / "ILSVRC2012_img_train.tar",
        val_tar=root_path / "ILSVRC2012_img_val.tar",
        target=root_path / f"compressed_batch={args.batch_size}",
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )
    
    sharder.start()
    print("Finished.")
