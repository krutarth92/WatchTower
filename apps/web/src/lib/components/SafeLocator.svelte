<script lang="ts">
	import { safeHttpLocator } from '#lib/presentation/locator.ts';
	let { value, label = 'Open source' }: { value: string | null; label?: string } = $props();
	const safe = $derived(safeHttpLocator(value));
</script>

{#if safe}
	<a href={safe.href} target="_blank" rel="noopener noreferrer"
		>{label}<span aria-hidden="true"> ↗</span></a
	>
{:else if value}
	<code title="This locator is displayed as text because its scheme is not allowed.">{value}</code>
{:else}
	<span class="unavailable">No locator supplied</span>
{/if}

<style>
	a {
		color: var(--color-primary);
		text-underline-offset: var(--space-1);
	}

	code,
	.unavailable {
		overflow-wrap: anywhere;
		color: var(--color-ink-muted);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
	}
</style>
