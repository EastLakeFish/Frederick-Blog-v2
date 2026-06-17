<script setup>
import { getCopyrightNow } from './copyright.ts'
</script>

<template>
    <p>{{ getCopyrightNow() }}</p>
</template>