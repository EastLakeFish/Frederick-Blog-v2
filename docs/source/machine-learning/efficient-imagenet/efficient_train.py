"""
(c) 2026 eastlakefish.com
This script implements an efficient ImageNet training script.

The code runs on single process.

"""

from __future__ import annotations

import argparse
import json
import numpy as np
import os
import random
from dataclasses import dataclass, asdict
from datetime import datetime
from functools import partial
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from loguru import logger
from tqdm import tqdm

import torch
from torch import nn, Tensor
from torch.utils.data import DataLoader
from torchvision.transforms import v2

import torchmetrics
from torchmetrics.classification import (
    MulticlassAccuracy,
    # MulticlassF1Score,
    # MulticlassRecall,
    # MulticlassPrecision
)

from efficient_imagenet import EfficientImageNet
from _models import default_parser, select_model, NUM_CLASSES


# ------ Preparation ------

OPTIMIZER = torch.optim.Adam
SCHEDULER = torch.optim.lr_scheduler.CosineAnnealingLR

LEARNING_RATE = 6.25e-2
LABEL_SMOOTHING = 1e-2
log_dir = "./runs"


def init_logger() -> None:
    global log_dir
    timestamp = datetime.now().timestamp()
    
    _log_dir = Path(log_dir) / str(timestamp)
    _log_dir.mkdir(parents=True, exist_ok=True)
    log_dir = _log_dir
    
    log_file = _log_dir / "runtime.log"
    logger.add(log_file, enqueue=True, level="INFO")
    
    
class Timer:
    def __init__(self, device: str | torch.device) -> None:
        self.on_cuda = str(device) != "cpu"
        self.start_event = None
        self._value = None
        
    def start(self) -> None:
        self.start_event = None
        if self.on_cuda:
            self.start_event = torch.cuda.Event(enable_timing=True)
            self.start_event.record()
        else:  # use perf_counter
            self.start_event = perf_counter()
            
    def stop(self) -> None:
        if self.start_event is None:
            raise RuntimeError("Timer hasn't been initialized.")
        if self.on_cuda:
            current = torch.cuda.Event(enable_timing=True)
            current.record()
            torch.cuda.synchronize()
            self._value = self.start_event.elapsed_time(current)  # type: ignore
        else:
            self._value = 1000 * (perf_counter() - self.start_event)  # type: ignore
            
    @property
    def value_ms(self) -> float:
        if self._value is None:
            raise RuntimeError("Call Timer.start() first.")
        return self._value
    
    @property
    def value_s(self) -> float:
        return self.value_ms / 1000
    
    @property
    def value_min(self) -> float:
        return self.value_s / 60
    
    @property
    def value_h(self) -> float:
        return self.value_min / 60

    def __enter__(self) -> Timer:
        self.start()
        return self
    
    def __exit__(self, *args, **kwargs) -> None:
        _, _ = args, kwargs
        self.stop()
        

def get_loaders(args: argparse.Namespace) -> tuple[DataLoader, DataLoader]:
    imagenet_mean = (0.485, 0.456, 0.406)
    imagenet_std = (0.229, 0.224, 0.225)

    transform = v2.Compose([
        v2.Resize(256, interpolation=v2.InterpolationMode.BILINEAR),
        v2.CenterCrop(224),
        v2.ToDtype(torch.float32, scale=True),
        v2.Normalize(mean=imagenet_mean, std=imagenet_std),
    ])
    
    dataset = partial(EfficientImageNet,
        root=args.dataset,
        device="cpu",  # for pin_memory
        transform=transform,
        num_workers=args.num_workers,
    )
    
    loader = partial(DataLoader,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        pin_memory=not args.no_pin_memory,
        prefetch_factor=args.prefetch_factor,
        persistent_workers=not args.no_persistent_workers
    )
    
    return (loader(dataset=dataset(split="train"), shuffle=True),
            loader(dataset=dataset(split="val"), shuffle=False))


def get_args() -> argparse.Namespace:
    parser = default_parser()  # arguments required by select_model
    
    parser.add_argument("-b", "--batch-size", type=int, default=256)
    parser.add_argument("-d", "--dataset", type=str, required=True)
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("-e", "--epochs", type=int, default=300)
    parser.add_argument("-lr", "--learning-rate", type=float, default=LEARNING_RATE)
    parser.add_argument("-w", "--num-workers", type=int, default=8)
    parser.add_argument("--prefetch-factor", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    
    parser.add_argument("--no-autocast", action="store_true")
    parser.add_argument("--no-pin-memory", action="store_true")
    parser.add_argument("--no-persistent-workers", action="store_true")
    
    return parser.parse_args()


def seed(args: argparse.Namespace) -> None:
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)


@dataclass
class Runtime:  # record runtime states
    # args
    args: argparse.Namespace
    
    # model
    model: nn.Module
    
    # utilities
    autocast: torch.amp.autocast_mode.autocast
    device: torch.device
    device_type: str
    grad_scalar: torch.amp.grad_scaler.GradScaler
    loss_fn: nn.Module
    optimizer: torch.optim.Optimizer
    scheduler: torch.optim.lr_scheduler.LRScheduler
    
    # metrics
    metrics: torchmetrics.MetricCollection
    
    # status
    epochs: int
    epoch_id: int = 0
    best_acc: float | None = None
    _legacy_ckpt_label: str | None = None
    
    def __post_init__(self) -> None:
        setattr(self, "best_acc", -1)
    
    def clear_metrics(self) -> None:
        self.metrics.reset()
        
    @staticmethod
    def _gen_ckpt_filename(ckpt_label: str) -> str:
        return f"best_{ckpt_label}.pt"
        
    def finish_epoch(self, val_acc: float) -> None:
        self.epoch_id += 1
        if val_acc >= (self.best_acc or -1):
            self.best_acc = val_acc
            ckpt_label = f"{100*val_acc:.4f}".replace(".", "_")  # e.g., 55_4321 <=> 55.4321%
            
            # add new checkpoint
            torch.save(self.model.state_dict(), log_dir / self._gen_ckpt_filename(ckpt_label))  # type: ignore
            
            # remove legacy checkpoint
            if self._legacy_ckpt_label is not None:
                os.unlink(log_dir / self._gen_ckpt_filename(self._legacy_ckpt_label))  # type: ignore
            self._legacy_ckpt_label = ckpt_label


def initialization(args: argparse.Namespace) -> Runtime:
    # high-performance specifications
    torch.backends.cudnn.benchmark = True
    torch.set_float32_matmul_precision("high")
    
    device = torch.device(args.device)
    model = select_model(args=args).to(device)
    optimizer = OPTIMIZER(params=model.parameters(), lr=args.learning_rate)
    
    return Runtime(
        args=args,
        model=model,
        device=device,
        device_type=device.type,
        epochs=args.epochs,
        loss_fn=torch.nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING),
        autocast=torch.amp.autocast(  # type: ignore
            device_type=device.type,
            enabled=not args.no_autocast,
            dtype=torch.float16,
        ),
        grad_scalar=torch.amp.grad_scaler.GradScaler(device=device.type, enabled=True),
        optimizer=optimizer,
        scheduler=SCHEDULER(optimizer, T_max=args.epochs),
        metrics=torchmetrics.MetricCollection({
            "top-1": MulticlassAccuracy(num_classes=NUM_CLASSES, top_k=1),
            "top-5": MulticlassAccuracy(num_classes=NUM_CLASSES, top_k=5),
            # "f1": MulticlassF1Score(num_classes=NUM_CLASSES),
            # "prec": MulticlassPrecision(num_classes=NUM_CLASSES),
            # "recall": MulticlassRecall(num_classes=NUM_CLASSES),
        }).to(device)
    )
    
    
@dataclass
class Result:
    type: Literal["train", "val"]
    elapsed_time_s: float
    metrics: dict[str, Any]
    
    def __post_init__(self) -> None:
        for metric_key, metric_item in self.metrics.items():
            if isinstance(metric_item, Tensor):
                self.metrics[metric_key] = metric_item.item()
    
    @property
    def elapsed_time_min(self) -> float:
        return self.elapsed_time_s / 60
    
    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            return self.metrics[item]
        
    def report(self) -> str:
        return (
            f"Elapsed: {self.elapsed_time_min:.2f}min | "
            + " | ".join(f"{key[0].capitalize() + key[1:]}: {item:.4f}" for key, item in self.metrics.items())
        )
    

# ------ Training ------

def train_one_epoch(state: Runtime, loader: DataLoader) -> Result:
    state.model.train()
    state.clear_metrics()
    timer = Timer(state.device_type)
    
    with timer:
        for features, labels in tqdm(loader, desc=f"[Train] Epoch {state.epoch_id}"):
            features, labels = features.to(state.device, non_blocking=True), labels.to(state.device, non_blocking=True)
            state.optimizer.zero_grad()
            with state.autocast:
                logits = state.model(features)
                loss = state.loss_fn(logits, labels)
            state.grad_scalar.scale(loss).backward()
            state.grad_scalar.step(state.optimizer)
            state.grad_scalar.update()
            state.metrics.update(logits, labels)
            
        state.scheduler.step()
    
    return Result(
        type="train",
        elapsed_time_s=timer.value_s,
        metrics=state.metrics.compute(),
    )


def val_one_epoch(state: Runtime, loader: DataLoader) -> Result:
    state.model.eval()
    state.clear_metrics()
    timer = Timer(state.device_type)
    
    with timer:
        with torch.no_grad():
            for features, labels in tqdm(loader, desc=f"[Val] Epoch {state.epoch_id}"):
                features, labels = features.to(state.device, non_blocking=True), labels.to(state.device, non_blocking=True)
                with state.autocast:
                    logits = state.model(features)
                state.metrics.update(logits, labels)
    
    return Result(
        type="val",
        elapsed_time_s=timer.value_s,
        metrics=state.metrics.compute(),
    )


# ------ Main Logic ------

def log_results(train_result: Result, val_result: Result) -> None:
    with open(log_dir / "results.jsonl", "a") as f:  # type: ignore
        f.write(json.dumps({
            "train": asdict(train_result),
            "val": asdict(val_result)
        }))
        f.write("\n")
            

def main() -> None:
    init_logger()
    
    args = get_args()
    seed(args)
    runtime = initialization(args)
    
    timer = Timer(runtime.device_type)
    
    with timer:
        train_loader, val_loader = get_loaders(args)
    logger.info(f"Dataset cached. Elapsed time: {timer.value_s:.2f} seconds.")
    
    # traininig logic
    try:
        with timer:
            for epoch_id in range(runtime.epochs):
                train_result = train_one_epoch(runtime, train_loader)
                logger.info(train_result.report())
                val_result = val_one_epoch(runtime, val_loader)
                logger.info(val_result.report())
                log_results(train_result, val_result)
                runtime.finish_epoch(val_result.metrics["top-1"])
                logger.info(f"[INFO] Epoch {epoch_id} finished. Elapsed time: {timer.value_min:.2f} minutes.")
    except KeyboardInterrupt:
            logger.info("Program terminated by user.")
    finally:
        logger.info(f"Program finished. Training took {timer.value_h:.2f} hours.")


if __name__ == "__main__":
    main()
