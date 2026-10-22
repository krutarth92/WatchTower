<script lang="ts">
	import type { Snippet } from 'svelte';
	let { children }: { children: Snippet } = $props();
</script>

<div class="grid-surface">{@render children()}</div>

<style>
	.grid-surface {
		background-color: var(--color-canvas);
		background-image: var(--gradient-ambient), var(--texture-grid);
		background-size:
			auto,
			var(--grid-size) var(--grid-size);
	}
</style>
