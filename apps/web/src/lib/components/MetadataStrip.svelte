<script lang="ts">
	let { items }: { items: readonly { label: string; value: string }[] } = $props();
</script>

<dl>
	{#each items as item (item.label)}
		<div>
			<dt>{item.label}</dt>
			<dd>{item.value}</dd>
		</div>
	{/each}
</dl>

<style>
	dl {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		margin: 0;
		border-top: var(--border-width) solid var(--color-border);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	div {
		padding: var(--space-3) var(--space-4);
		border-left: var(--border-width) solid var(--color-border);
	}

	div:first-child {
		border-left: 0;
	}

	dt {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	dd {
		margin: var(--space-1) 0 0;
		font-weight: 650;
	}

	@media (max-width: 40rem) {
		div:nth-child(odd) {
			border-left: 0;
		}
	}
</style>
