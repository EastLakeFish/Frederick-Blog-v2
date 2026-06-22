---
title: Compressed ImageNet
description: Introduces ImageNet sharding and compression

prev: false
next: {
    text: "Efficient ImageNet",
    link: "../efficient-imagenet/index"
}

references:
    qimeng2019:
        title: Convergence Analysis of Distributed Stochastic Gradient Descent with Shuffling
        authors: Qi Meng, et al
        book: Neurocomputing
        year: 2019

---

# Sharding ImageNet

*Created on June 11, 2026.*

:::info **This article belongs to series** [*Efficient ImageNet*](/notes/machine-learning/index)
:::

<div class="update-notes">
  <h1>Update Notes</h1>
  <div class="update-note">
    <span class="date">2026-06-15</span>
    <span class="message">Caching and encoding labels in filenames.</span>
  </div>
</div>

ImageNet has been one of the standard benchmark datasets that are frequently used in computer vision tasks.
However, it is also notorious for its size - over one million training samples, taking up approximately 140-160GB of storage.
This makes ImageNet extremely heavy for many training pipelines.
In addition, the raw training set has nested tars, making it difficult to shuffle without extracting the files.
And if you extract them, randomly accessing these files will become another bottleneck on the filesystem side.

In this article, we slim down ImageNet through sharding, making it easy to access, distribute, and suitable for DNN training.
We also provide a script for global shuffling as an example of using the sharded dataset.
The programs and examples are written in Python.

Due to ImageNet restrictions, a copy of the processed data will not be provided on this page.
You can find our source files at the <a href="#source-files">bottom</a> of this page.

## Implementation

Sharding means to partition a large dataset into smaller chunks (e.g., tars).
Compared with reading tens of thousands of individual files, reading those chunks can be extremely fast, because each chunk is considered a single file from the filesystem perspective.

::: tip **Should chunks be as large as possible?**
Not necessarily.
Since samples are shuffled during training, a larger chunk requires a shuffling buffer that occupies more space in RAM.
A compromise between reading speed and RAM usage is using small-to-medium chunks, e.g., 1,000-10,000 images/chunk.
:::

<figure class="fig-md" style="width: 80%;">
<img src="./assets/sharding.svg" alt="Sharding">
<figcaption>
<strong>Fig. 1.</strong>
Sharding ImageNet:
Images are first resized to 224x224, and then randomly saved in shards.
This processes use multiple working threads.
</figcaption>
</figure>

### Download

The official ImageNet data are provided in tar files.
You can download these files from the official [website](https://www.image-net.org/index.php).
Take ILSVRC 2012 as an example, we need the following files:

|File Name|Size|
|-|-|
|ILSVRC2012_devkit_t12.tar.gz|2.5MB|
|ILSVRC2012_img_train.tar|140GB|
|ILSVRC2012_img_val.tar|6GB|

Do not extract any file from those tars, and just put them in the same directory.
In ImageNet, each category belongs to a WordNet ID (WNID), which is also used to name the directory of the corresponding images.
For example, the WNID &ldquo;n02084071&rdquo; refers to a noun (&ldquo;n&rdquo;) with an index &ldquo;02084071&rdquo;, which means &ldquo;dogs&rdquo;.
To map WNID to standard English, you can use the `nltk` library.

### Data Integrity

To check whether the downloaded datasets are complete, we need the `tarfile` library, which is built-in in Python (see official [docs](https://docs.python.org/3/library/tarfile.html)).
The reader, `tarfile.open`, supports `with` statement and two modes:

|Mode|Symbol|Feature|
|-|-|-|
|Random Seeking|`"r"`|Load tar structures in memory, convenient for non-sequential reading.|
|Streaming|`"r\|"`|Read bytes sequentially, low memory occupation.|

The official training split uses a nested structure, where images belonging to the same category are saved in a tar named with the corresponding WNID.
On the other hand, the tar for validation set contains unlabeled images.
To check the integrity of ImageNet, we can use the following script:

``` python
def inspect_imagenet(root: str):
    num_classes, train_samples, val_samples = 0, 0, 0
    start = time.time()

    # inspect train set
    pbar = tqdm.tqdm(total=1000, desc="Inspect train")  # requires tqdm
    with tarfile.open(os.path.join(root, "ILSVRC2012_img_train.tar"), "r") as tar_train:
        subtars = list(tar_train.getmembers())
        num_classes = len(subtars)
        for subtar in subtars:
            subtar_stream = tar_train.extractfile(subtar)
            with tarfile.open(fileobj=subtar_stream, mode="r|") as subtar:
                train_samples += len(list(subtar.getmembers()))
            pbar.update()
    
    # inspect val set
    with tarfile.open(os.path.join(root, "ILSVRC2012_img_val.tar"), "r") as tar_val:
        val_samples = len(list(tar_val.getmembers()))
    
    print(f"Classes: {num_classes} | Train: {train_samples} | Val: {val_samples} | Elapsed: {int(time.time() - start)}s.")
```

The output should match the official report:
``` text
Classes: 1000 | Train: 1281167 | Val: 50000 | Elapsed: 636s.
```

### Sharding

The ImageNet sharder employs multiple workers to shard ImageNet efficiently.
Its framework is shown in <a href="#fig:sharder">Fig. 2</a>.

<figure class="fig" id="fig:sharder">
<img src="./assets/sharder.svg" alt="Sharder">
<figcaption>
<strong>Fig. 2.</strong>
The framework of sharder.
It employs a main thread, a collector thread and multiple worker threads.
</figcaption>
</figure>

Once executed, the sharder will spawn multiple threads, where we run a collector and an arbitrary number of workers.
There are two types of workers.
For the training set, the main thread reads nested tars and put them in the input queue, thus workers receive bytes of those nested tars, streaming them and processing images inside them.
For validation set, the main thread loads raw image bytes, thus workers process these images directly.
The processed image bytes, along with their labels (for training set), are gathered by the collector, where they are saved to shard files.

### Benchmark

Through sharding, the ImageNet dataset can be compressed into shard files of only 14GB, while the original data take up approximately 150GB on disk, yielding a compression rate of 90%.
On HDD with I/O bandwidth 210MB/s, a sharder with 16 workers takes only 13 minutes to process the whole dataset.
On SSD, it takes approximately 8 minutes.

<figure class="fig-md">
<img src="./assets/results.png" alt="Sharding Results">
<figcaption>
<strong>Fig. 3.</strong>
Generated files in shards.
Labels (shadowed in yellow) are encoded in filenames.
</figcaption>
</figure>

## Shuffling

Many DNN optimizers value the stochasticity of samples, requiring the data to be shuffled before training.
For ImageNet, there are so many samples that shuffling becomes difficult.
For a sharded dataset, we have two approaches for shuffling:

- **Global Shuffling.** Organize image paths into a list, and shuffle the list before loading.
- **Local Shuffling.** Shuffle shards first, then shuffle images in each shard.

Local shuffling can be easier to implement, and is widely used in modern datasets such as WebDataset.
However, it doesn't yield full stochasticity and might affect convergence speed.
Recent work <a href="#qimeng2019">[1]</a> shows local shuffling can lead to a lower convergence rate.
Therefore, global shuffling is preferred when the hardware permits.

We only shuffle on the training set.
Before global shuffling, it is important to build up a database to store image information.
To achieve that, we still employ multiple workers to iterate over different shards and gather image information within those shards.
The framework to build up this database is similar to the sharder shown in <a href="#fig:sharder">Fig. 2</a>.

On SSD, the script takes approximately 30 seconds to shuffle the sharded data using a single worker, about 15 seconds with 2 workers, and about 7 seconds with 4 or more workers.

**Example.** First 5 samples in a shuffled file list:
``` python
# pattern: shard_id/label.filename (with suffix)
# train set
[
    '112/657.n03773504_14704.JPEG', 
    '16/883.n04522168_6421.JPEG', 
    '119/704.n03891332_259.JPEG', 
    '110/640.n03717622_8920.JPEG', 
    '37/123.n01984695_15603.JPEG'
]

# val set
[
    '0/660.ILSVRC2012_val_00046108.JPEG', 
    '1/530.ILSVRC2012_val_00046901.JPEG', 
    '3/431.ILSVRC2012_val_00046599.JPEG', 
    '2/268.ILSVRC2012_val_00038956.JPEG', 
    '0/660.ILSVRC2012_val_00031091.JPEG'
]
```

## Source Files

<SourceFileCard
href="machine-learning/sharding-imagenet/sharder.py"
desc="ImageNet sharding pipeline implementation."
/>

<SourceFileCard
href="machine-learning/sharding-imagenet/shuffle.py"
desc="A shuffler for sharded ImageNet data."
/>