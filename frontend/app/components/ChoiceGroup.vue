<script setup lang="ts" generic="T extends string">
/** Segmented control, keyboard-accessible as radios. */
defineProps<{ choices: { value: T, label: string }[], label: string }>()
const model = defineModel<T>({ required: true })
</script>

<template>
  <div role="radiogroup" :aria-label="label" class="flex flex-wrap items-center gap-1">
    <button
      v-for="c in choices"
      :key="c.value"
      type="button"
      role="radio"
      :aria-checked="model === c.value"
      class="cursor-pointer rounded-full border px-3 py-1 text-sm"
      :class="model === c.value ? 'border-accent bg-accent text-accent-ink' : 'border-line hover:border-line-strong'"
      @click="model = c.value"
    >
      {{ c.label }}
    </button>
  </div>
</template>
