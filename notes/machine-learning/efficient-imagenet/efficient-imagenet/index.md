---
title: Efficient ImageNet
description: Building efficient ImageNet datasets.

prev: {
    text: "Sharding ImageNet",
    link: "../sharding-imagenet/index",
}

next: {
    text: "Parallel Training",
    link: "../parallel-training/index"
}
---

# Efficient ImageNet

*Created on June 15, 2026*

:::info **This article belongs to series** [*Efficient ImageNet*](/notes/machine-learning/index)
:::

While sharding makes it efficient to stream data from a large dataset, the implementation, especially for reshuffling before each epoch starts, becomes very complex.
This is because we have to avoid random seeking in the shards, as it generally takes longer than directly reading files from the filesystem.
To improve efficiency, we can also consider a pre-indexing approach where we use multiple processes to scan the shards, and build up a map between the important metadata and actually offsets of the data.
For example, we need something like:

```python
preindexed = [{
    "filename": "n01440764_18.JPEG",
    "shard_id": 0,
    "offset_data": 64,
    "size": 22984,
    "label": 0,
}]  # example
```

And when loading the data, we seek the offsets instead of locating the files with their names:

```python
random.shuffle()
for item in preindexed:
    with open(f"shard_{item['shard_id']}.tar") as tar:
        tar.seek(item["offset_data"])
        img_bytes = tar.read(item["size"])
    image = Image.open(io.BytesIO(img_bytes))
```

The above is the general idea of building an efficient ImageNet dataset based on sharded data.
In fact, this idea can also be applied to the raw ImageNet data (i.e., nested tar files), which is simply less direct and requires more dataset-specific implementations.

## Implementation

To deal with arbitrary sharded datasets, we don't assume we have the sharder file (see [previous](../sharding-imagenet/index) note) and start with data structure inspection.
We assume the sharded dataset has the following structure:

```text
ROOT
  ├── train
  │     └── shard_0.tar, ...
  │           └── <label>.<filename>.<suffix>
  └── val
        └── shard_0.tar, ...
              └── <label>.<filename>.<suffix>
```

We still assign the shards to multiple worker processes to pre-indexing data.
Each data block corresponds to one image, which is in the following structure:

```python
{
    "shard": shard_path,
    "label": mem.name.split(".")[0],
    "offset": mem.offset_data,
    "size": mem.size,
}
```

Through multiprocessing, iterating the whole ImageNet dataset typically uses less than 20 seconds.

Next, we implement `__getitem__` and `__len__` so that the dataset can work with PyTorch `DataLoader`.
In particular, we employ `torchvision.io.decode_image` to directly decode image bytes in memory:

```python
buf = torch.frombuffer(img_bytes, dtype=torch.uint8)
img = torchvision.io.decode_image(buf, mode="RGB")  # if the sharder uses RGB
```

## Results

Setting `num_workers` to 8 for `DataLoader`, we evaluate the performance of our efficient dataset by running 10 warmup batches and 500 <q>training</q> batches (loading data and then do nothing).
The results are shown as follows:

|Batch Size|Samples/Sec|Batches/Sec|Avg Speed|
|-|-|-|-|
|256|21112.03|82.47|0.047ms/sample|

## Source Files

<a href="/docs/source/?file=machine-learning/efficient-imagenet/efficient_imagenet.py" class="source-link">
<span class="file">efficient_imagenet.py</span>
<span class="desc">An efficient ImageNet dataset for sharded data (single-card training).</span>
</a>