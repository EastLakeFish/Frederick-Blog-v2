<script setup>

const props = defineProps({
    history: {
        type: Map,
        required: true,
    }
})

</script>

<template>

<div class="update-notes">
  <h1>Update Notes</h1>
  <div class="update-note" v-for="(msg, date) in props.history">
    <span class="date">{{ date }}</span>
    <span class="message">{{ msg }}</span>
  </div>
</div>

</template>