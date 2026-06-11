---
title: Parallel Training with PyTorch
description: Using DDP-based approaches to train models on multiple graphics cards.

prev: {
    text: "Compressed ImageNet",
    link: "../compressed-imagenet/index"
}
next: false

---

# Parallel Training with PyTorch

::: info **This article belongs to series** [*Efficient ImageNet*](../index.md)
:::

Training on multiple graphics cards can be mathematically equivalent to single-card training.
It is just sometimes prohibitive due to challenges such as CPU/memory bottleneck, and the difficulty in implementing the training utilities.

An important lesson taught by the CPU bottleneck is that part of the preprocessing jobs belongs to somewhere outside the training script, especially when you plan to use two graphics cards.
Take ImageNet for example, since `DataLoader` generally does not hold old batch cache, images need to be resized at the beginning of every batch.
This leads to 1.28 million resize operations per epoch, and 128 million if you were to train for 100 epochs, while these operations are totally avoidable.

For compressing ImageNet and avoiding resizing during training, please refer to the [previous](../compressed-imagenet/index.md) note.
In this article, we will design utilities for parallel training on ImageNet with techniques brought by PyTorch Distributed Data Parallel (DDP).
You can find an official tutorial on DDP [here](https://docs.pytorch.org/tutorials/intermediate/ddp_tutorial.html).
