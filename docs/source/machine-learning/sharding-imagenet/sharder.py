"""
(c) 2026 eastlakefish.com
This script implements a sharder for ImageNet dataset.

This code is open-source under GNU GPL v2.0.
See https://eastlakefish.com/license.html.

"""

from __future__ import annotations

import io
import json
import tarfile

import scipy.io as sio

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
    result = buf.getvalue()
    buf.close()
    return result


def _worker_train(wnid2label: dict, tar_queue: Queue, img_queue: Queue) -> None:
    while True:
        d = tar_queue.get()
        if d is None:
            break
        tar_name, tar_bytes = d
        tar_name = tar_name.split(".")[0]  # remove suffix
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r|") as tar:
            while member := tar.next():  # JPEG
                handler = tar.extractfile(member)
                if handler:
                    try:
                        img_queue.put((wnid2label[tar_name], member.name, _process_img(handler.read())))
                    except:
                        continue
                    
                    
def _worker_val(val_filename2label: dict, in_queue: Queue, out_queue: Queue) -> None:
    while True:
        d = in_queue.get()
        if d is None:
            break
        img_name, img_bytes = d
        try:
            out_queue.put((f"{val_filename2label[img_name]}.{img_name}", _process_img(img_bytes)))
        except:
            continue


def _collector(root: Path, batch_size: int, img_queue: Queue, total: int) -> None:
    def sharder_filename(c: int) -> Path:
        return root / f"shard_{c}.tar"
    
    root.mkdir(parents=True, exist_ok=True)
    
    shard_id, shard_counter = 0, 0
    pbar = tqdm(total=total, desc="Processing")
    target_tar = tarfile.open(sharder_filename(shard_id), "w|")
    try:
        while True:
            d = img_queue.get()
            if d is None:
                break
            if len(d) == 3:  # train set
                label, filename, img_bytes = d
                file_info = tarfile.TarInfo(".".join((str(label), filename)))
            else:  # val set
                filename, img_bytes = d
                file_info = tarfile.TarInfo(filename)
            file_info.size = len(img_bytes)
            target_tar.addfile(file_info, io.BytesIO(img_bytes))
            if shard_counter >= batch_size:
                shard_id += 1
                shard_counter = 0
                target_tar.close()
                target_tar = tarfile.open(sharder_filename(shard_id), "w|")
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
        devkit_tar: str | Path,
        target: str | Path,
        batch_size: int = 10_000,
        num_workers: int = 8,
    ) -> None:
        self.paths = dict(train=Path(train_tar), val=Path(val_tar))
        self.wnid2label = self._wnid2label(Path(train_tar))
        self.target = Path(target).expanduser()
        self.target.mkdir(parents=True, exist_ok=True)
        
        self.meta = self.inspect()
        self.batch_size = batch_size
        self.num_workers = num_workers
        
        self.val_wnids, self.ilsvrc_id2wnid = self.load_devkit(Path(devkit_tar))
        self.val_filename2label = self._val_filename2label()
        
        train_wnids = set(self.wnid2label)
        devkit_wnids = set(self.ilsvrc_id2wnid.values())

        if train_wnids != devkit_wnids:
            missing_from_devkit = train_wnids - devkit_wnids
            missing_from_train = devkit_wnids - train_wnids

            raise RuntimeError(
                "Training archive and devkit class sets differ.\n"
                f"Missing from devkit: {sorted(missing_from_devkit)[:10]}\n"
                f"Missing from train: {sorted(missing_from_train)[:10]}"
            )

        validation_labels = set(self.val_filename2label.values())

        if validation_labels != set(range(1_000)):
            raise RuntimeError(
                "Validation mapping does not cover labels 0-999"
            )
        
        self._save_cache(self.val_filename2label, self.target / "val_filename2label.json")
        self._save_cache(self.meta, self.target / "meta.json")
        self._save_cache(self.wnid2label, self.target / "wnid2label.json")
        
    @staticmethod
    def _save_cache(d: dict, f: Path) -> None:
        with open(f, "w") as _f:
            json.dump(d, _f, indent=2)
        
    @staticmethod
    def load_devkit(path: Path) -> tuple[list[str], dict[int, str]]:
        devkit_prefix = "ILSVRC2012_devkit_t12/data"

        ground_truth_path = (
            f"{devkit_prefix}/"
            "ILSVRC2012_validation_ground_truth.txt"
        )
        meta_path = f"{devkit_prefix}/meta.mat"

        with tarfile.open(path, "r:gz") as tar:
            gt_handler = tar.extractfile(ground_truth_path)
            meta_handler = tar.extractfile(meta_path)

            if gt_handler is None:
                raise RuntimeError(
                    f"Cannot extract {ground_truth_path}"
                )

            if meta_handler is None:
                raise RuntimeError(
                    f"Cannot extract {meta_path}"
                )

            validation_ids = [
                int(line)
                for line in gt_handler.read()
                .decode("utf-8")
                .splitlines()
            ]

            meta_bytes = meta_handler.read()

        synsets = sio.loadmat(
            io.BytesIO(meta_bytes),
            squeeze_me=True,
        )["synsets"]

        # meta.mat contains both the 1,000 ImageNet classes and
        # internal WordNet nodes. ImageNet classes are leaf nodes,
        # whose number of children is zero
        num_children = list(zip(*synsets))[4]

        leaf_synsets = [
            synsets[index]
            for index, children in enumerate(num_children)
            if int(children) == 0
        ]

        ilsvrc_ids, wnids = list(zip(*leaf_synsets))[:2]

        ilsvrc_id2wnid = {
            int(ilsvrc_id): str(wnid)
            for ilsvrc_id, wnid in zip(ilsvrc_ids, wnids)
        }

        if len(ilsvrc_id2wnid) != 1_000:
            raise RuntimeError(
                "Expected 1,000 leaf synsets, found "
                f"{len(ilsvrc_id2wnid)}"
            )

        if len(validation_ids) != 50_000:
            raise RuntimeError(
                "Expected 50,000 validation labels, found "
                f"{len(validation_ids)}"
            )

        try:
            validation_wnids = [
                ilsvrc_id2wnid[ilsvrc_id]
                for ilsvrc_id in validation_ids
            ]
        except KeyError as exc:
            raise RuntimeError(
                f"Unknown ILSVRC class ID in validation labels: {exc}"
            ) from exc

        return validation_wnids, ilsvrc_id2wnid
    
    @staticmethod
    def _wnid2label(train_tar: Path) -> dict:
        with tarfile.open(train_tar, "r") as tar:
            return {wnid: label for label, wnid in enumerate(sorted(
                mem.name.split(".")[0] for mem in tar.getmembers() if (mem.isfile() and mem.name.endswith(".tar"))
            ))}  # range 0-999
    
    def _val_filename2label(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in self.meta["val"]:
            filename = Path(item["name"]).name
            if not filename.lower().endswith((".jpeg", ".jpg", ".png")):
                continue
            # example: ILSVRC2012_val_00000001.JPEG
            image_number_text = Path(filename).stem.rsplit("_", 1)[-1]
            try:
                image_index = int(image_number_text) - 1
            except ValueError as exc:
                raise RuntimeError(
                    f"Unexpected validation filename: {filename!r}"
                ) from exc
            if not 0 <= image_index < len(self.val_wnids):
                raise RuntimeError(
                    f"Validation image index out of range: "
                    f"{filename!r} -> {image_index}"
                )
            wnid = self.val_wnids[image_index]
            try:
                label = self.wnid2label[wnid]
            except KeyError as exc:
                raise RuntimeError(
                    f"Validation WNID {wnid!r} does not occur "
                    "in the training archive"
                ) from exc
            result[filename] = label

        if len(result) != 50_000:
            raise RuntimeError(
                f"Expected 50,000 validation images, found {len(result)}"
            )
        return result
    
    def inspect(self) -> dict:
        def _inspect(tar) -> list:
            with tarfile.open(tar, "r") as tar:
                return list({
                    "name": member.name,  # for train set, these are tars
                    "size": member.size,
                    "offset": member.offset_data,
                } for member in tar.getmembers())
        return {k: _inspect(v) for k, v in self.paths.items()}
        
    def _assign(self, split: str, queue: Queue) -> None:
        with open(self.paths[split], "rb") as f:
            for meta in self.meta[split]:
                f.seek(meta["offset"])
                queue.put((
                    meta["name"],
                    f.read(meta["size"]),
                ))
        for _ in range(self.num_workers):
            queue.put(None)
    
    def start(self) -> None:
        # process train set
        tar_queue = Queue(maxsize=20 * self.num_workers)
        img_queue = Queue()
        workers = [Process(target=_worker_train, args=(self.wnid2label, tar_queue, img_queue)) for _ in range(self.num_workers)]
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
        workers = [Process(target=_worker_val, args=(self.val_filename2label, in_queue, out_queue)) for _ in range(self.num_workers)]
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
    parser.add_argument("-o", "--out", type=str, default=None)
    args = parser.parse_args()
    
    root_path = Path(args.root[0])
    
    sharder = ImageNetSharder(
        train_tar=root_path / "ILSVRC2012_img_train.tar",
        val_tar=root_path / "ILSVRC2012_img_val.tar",
        devkit_tar=root_path / "ILSVRC2012_devkit_t12.tar.gz",
        target=args.out or root_path / f"compressed_batch={args.batch_size}",
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )
    
    sharder.start()
    print("Finished.")
