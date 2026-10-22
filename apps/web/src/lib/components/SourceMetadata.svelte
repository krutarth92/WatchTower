<script lang="ts">
	import type { SourceRead } from '#lib/api/contracts.ts';
	let { source, nativeId }: { source: SourceRead; nativeId?: string | null } = $props();
</script>

<div class="source">
	<div>
		<span>SOURCE</span>
		<strong>{source.name}</strong>
	</div>
	<div>
		<span>KIND</span>
		<strong>{source.kind}</strong>
	</div>
	{#if nativeId}
		<div>
			<span>NATIVE ID</span>
			<code>{nativeId}</code>
		</div>
	{/if}
</div>

<style>
	.source {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-5);
		padding: var(--space-3) var(--space-4);
		border-left: 0.1875rem solid var(--color-primary);
		background: var(--color-primary-faint);
	}

	.source div {
		display: grid;
		gap: var(--space-1);
	}

	span {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	strong,
	code {
		color: var(--color-ink);
		font-size: var(--font-size-sm);
	}
</style>
