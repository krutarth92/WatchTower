<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		eyebrow,
		title,
		compact = false,
		children
	}: { eyebrow?: string; title?: string; compact?: boolean; children: Snippet } = $props();
</script>

<section class:compact>
	{#if eyebrow || title}
		<header>
			{#if eyebrow}<p>{eyebrow}</p>{/if}
			{#if title}<h2>{title}</h2>{/if}
		</header>
	{/if}
	<div class="content">{@render children()}</div>
</section>

<style>
	section {
		position: relative;
		overflow: hidden;
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-lg);
		background: var(--gradient-surface), var(--color-surface);
		box-shadow: var(--shadow-panel);
	}

	section::before {
		position: absolute;
		top: 0;
		left: 0;
		width: var(--space-6);
		height: var(--border-width);
		background: var(--gradient-brand);
		content: '';
	}

	header {
		padding: var(--space-4) var(--space-5);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	header p {
		margin: 0;
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	h2 {
		margin: var(--space-1) 0 0;
		font-size: var(--font-size-lg);
	}

	.content {
		padding: var(--space-5);
	}

	.compact .content {
		padding: var(--space-4);
	}
</style>
