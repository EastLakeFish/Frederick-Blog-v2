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

:::info **This article belongs to series** [*Efficient ImageNet*](../index.md)
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