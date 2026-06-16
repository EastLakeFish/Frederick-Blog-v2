<script setup>
const props = defineProps({
  roots: {
    type: Array,
    default: () => ["notes"],
  },
  mode: {
    type: String,
    default: "full", // "full" or "topic"
  },
})

const child = "├── "
const lastChild = "└── "

function slug2title(slug = "") {
  return slug
    .split("-")
    .filter(Boolean)
    .map(word => {
      const capitals = [...word].filter(
        ch => ch >= "A" && ch <= "Z"
      ).length

      if (capitals >= 1) {
        return word
      }

      return word[0].toUpperCase() + word.slice(1)
    })
    .join(" ")
}
function normalizeRoot(root) {
  return root.split("/").filter(Boolean).join("/")
}

function dirOf(path) {
  return path
    .split("/")
    .filter(Boolean)
    .slice(0, -1)
    .join("/")
}

function getOrder(path) {
  const name = path.split("/").filter(Boolean).at(-1)
  const match = name?.match(/^content-(\d+)$/)
  return match ? Number(match[1]) : Infinity
}

function isUnderRoot(page, root) {
  const rootParts = normalizeRoot(root).split("/")

  if (page.parts.length < rootParts.length) {
    return false
  }

  return rootParts.every(
    (part, index) => page.parts[index] === part
  )
}

function partsEqualPrefix(parts, prefixParts) {
  if (parts.length < prefixParts.length) return false

  return prefixParts.every(
    (part, index) => parts[index] === part
  )
}

function pageOrder(page) {
  return orderMap[page.parts.join("/")] ?? Infinity
}

function comparePages(a, b) {
  return pageOrder(a) - pageOrder(b) || a.path.localeCompare(b.path)
}

const roots = props.roots.map(normalizeRoot)

const orderFiles = Object.keys(
  import.meta.glob("/**/content-*")
)

const orderMap = {}

for (const path of orderFiles) {
  orderMap[dirOf(path)] = getOrder(path)
}

const pages = Object.keys(import.meta.glob("/**/index.md"))
  .map(path => {
    const parts = path
      .split("/")
      .filter(Boolean)
      .slice(0, -1)

    return {
      path,
      parts,
      link: "/" + parts.join("/") + "/",
      depth: parts.length - 1,
      title: slug2title(parts.at(-1)),
    }
  })
  .filter(page =>
    page.parts.length > 0 &&
    roots.some(root => isUnderRoot(page, root))
  )
  .sort(comparePages)

const fullGroups = roots.map(root => ({
  root,
  title: slug2title(root.split("/").at(-1)),
  topics: [],
}))

for (const page of pages) {
  const group = fullGroups.find(group =>
    isUnderRoot(page, group.root)
  )

  if (!group) continue

  const rootDepth = group.root.split("/").length - 1

  if (page.depth <= rootDepth) continue

  const topicIndex = rootDepth + 1
  const topicKey = page.parts[topicIndex]

  let topic = group.topics.find(
    t => t.parts[topicIndex] === topicKey
  )

  if (!topic) {
    const topicParts = page.parts.slice(0, topicIndex + 1)

    topic = {
      path: "/" + topicParts.join("/") + "/index.md",
      parts: topicParts,
      link: "/" + topicParts.join("/") + "/",
      depth: topicParts.length - 1,
      title: slug2title(topicKey),
      children: [],
    }

    group.topics.push(topic)
  }

  if (page.parts.length === topic.parts.length) {
    Object.assign(topic, {
      ...page,
      children: topic.children,
    })
  } else {
    topic.children.push(page)
  }
}

for (const group of fullGroups) {
  group.topics.sort(comparePages)

  for (const topic of group.topics) {
    topic.children.sort(comparePages)
  }
}

const topicGroups = roots.map(root => {
  const rootParts = normalizeRoot(root).split("/")

  const children = pages
    .filter(page =>
      partsEqualPrefix(page.parts, rootParts) &&
      page.parts.length > rootParts.length
    )
    .sort(comparePages)

  return {
    root,
    children,
  }
})

console.log(
  roots,
  // topicGroups.map(g => ({
  //   root: g.root,
  //   children: g.children.map(p => p.parts.join("/")),
  // }))
)
</script>

<template>
  <template v-if="mode === 'full'">
    <template v-for="group in fullGroups" :key="group.root">
      <h2>{{ group.title }}</h2>

      <div class="tree-toc">
        <template v-for="topic in group.topics" :key="topic.path">
          <div>
            <a :href="topic.link">
              <span class="topic">{{ topic.title }}</span>
            </a>
          </div>

          <div
            v-for="(page, index) in topic.children"
            :key="page.path"
          >
            <a :href="page.link">
              {{
                index === topic.children.length - 1
                  ? lastChild
                  : child
              }}
              {{ page.title }}
            </a>
          </div>
        </template>
      </div>
    </template>
  </template>

  <template v-else>
    <div
      v-for="group in topicGroups"
      :key="group.root"
      class="tree-toc"
    >
      <div
        v-for="(page, index) in group.children"
        :key="page.path"
      >
        <a :href="page.link">
          {{
            index === group.children.length - 1
              ? lastChild
              : child
          }}
          {{ page.title }}
        </a>
      </div>
    </div>
  </template>
</template>