<script lang="ts">
	type Tone = 'observed' | 'assessed' | 'critical' | 'neutral' | 'ready';
	let { label, tone = 'neutral' }: { label: string; tone?: Tone } = $props();
</script>

<span class="chip {tone}"><span class="marker" aria-hidden="true"></span>{label}</span>

<style>
	.chip {
		display: inline-flex;
		min-height: 1.75rem;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-2);
		border: var(--border-width) solid currentColor;
		border-radius: var(--radius-sm);
		color: var(--color-ink-muted);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
		line-height: 1;
	}

	.marker {
		width: 0.45rem;
		height: 0.45rem;
		border: var(--border-width) solid currentColor;
		transform: rotate(45deg);
	}

	.observed,
	.ready {
		color: var(--color-observed);
	}

	.assessed {
		color: var(--color-assessed);
	}

	.critical {
		color: var(--color-critical);
	}

	.ready .marker {
		border-radius: 50%;
		transform: none;
		background: currentColor;
	}
</style>
