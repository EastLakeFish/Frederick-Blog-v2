<script setup>

const props = defineProps({
    href: {
        type: String,
        required: true,
    },
    desc: {
        type: String,
        required: true,
    },
    is_dir: {
        type: Boolean,
        required: false,
        default: false,
    }
})

const href = props.href.startsWith("/") ? props.href : '/docs/source/?file=' + props.href
const desc = props.desc
const filename = href.split("/").filter(Boolean).pop()

const icon = props.is_dir ? '📁' : '📄'

</script>

<template>
<a :href="href" class="source-link">
<span class="same-line">
<span class="icon">{{ icon }}</span>
<span class="file">{{ filename }}</span>
</span>
<span class="desc">{{ desc }}</span>
</a>
</template>