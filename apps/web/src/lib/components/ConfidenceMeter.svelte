<script lang="ts">
	let { value }: { value: number | null } = $props();
	const bounded = $derived(value === null ? 0 : Math.min(100, Math.max(0, value)));
</script>

<div class="confidence">
	<div class="label">
		<span>CONFIDENCE</span><strong>{value === null ? 'Not supplied' : `${bounded}%`}</strong>
	</div>
	{#if value !== null}
		<div
			class="track"
			role="meter"
			aria-label="Confidence"
			aria-valuenow={bounded}
			aria-valuemin="0"
			aria-valuemax="100"
		>
			<span style={`--confidence: ${bounded}%`}></span>
		</div>
	{/if}
</div>

<style>
	.confidence {
		display: grid;
		gap: var(--space-2);
	}

	.label {
		display: flex;
		justify-content: space-between;
		gap: var(--space-3);
	}

	.label span {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	.label strong {
		font-size: var(--font-size-sm);
	}

	.track {
		height: 0.35rem;
		overflow: hidden;
		border-radius: var(--radius-sm);
		background: var(--color-border);
	}

	.track span {
		display: block;
		width: var(--confidence);
		height: 100%;
		background: var(--gradient-brand);
	}
</style>
