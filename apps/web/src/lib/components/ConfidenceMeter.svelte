<script lang="ts">
	let { value }: { value: number | null } = $props();
	const bounded = $derived(value === null ? 0 : Math.min(100, Math.max(0, value)));
</script>

<div class="confidence">
	<div class="label">
		<span>CONFIDENCE</span><strong>{value === null ? 'Not supplied' : `${bounded}%`}</strong>
	</div>
	{#if value !== null}
		<progress class="track" aria-label="Confidence" value={bounded} max="100">
			{bounded}%
		</progress>
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
		width: 100%;
		height: 0.35rem;
		overflow: hidden;
		appearance: none;
		border: 0;
		border-radius: var(--radius-sm);
		background: var(--color-border);
	}

	.track::-webkit-progress-bar {
		background: var(--color-border);
	}

	.track::-webkit-progress-value {
		background: var(--gradient-brand);
	}

	.track::-moz-progress-bar {
		background: var(--gradient-brand);
	}
</style>
