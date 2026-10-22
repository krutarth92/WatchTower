<script lang="ts">
	type State = 'loading' | 'empty' | 'error';
	let {
		state,
		title,
		message,
		requestId,
		onRetry
	}: { state: State; title: string; message: string; requestId?: string; onRetry?: () => void } =
		$props();
</script>

<section
	class="state {state}"
	aria-live={state === 'loading' ? 'polite' : 'assertive'}
	aria-busy={state === 'loading'}
>
	<div class="state-icon" aria-hidden="true">
		{state === 'loading' ? '···' : state === 'empty' ? '○' : '!'}
	</div>
	<div>
		<h3>{title}</h3>
		<p>{message}</p>
		{#if requestId}<p class="request-id">Request ID: <code>{requestId}</code></p>{/if}
	</div>
	{#if state === 'error' && onRetry}<button type="button" onclick={onRetry}>Retry</button>{/if}
</section>

<style>
	.state {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		gap: var(--space-4);
		min-height: 7rem;
		padding: var(--space-4);
		border: var(--border-width) dashed var(--color-border-strong);
		border-radius: var(--radius-md);
		background: var(--color-surface-raised);
	}

	.state-icon {
		display: grid;
		width: 2.5rem;
		height: 2.5rem;
		place-items: center;
		border: var(--border-width) solid currentColor;
		border-radius: 50%;
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-weight: 800;
	}

	.error .state-icon {
		color: var(--color-critical);
	}

	h3,
	p {
		margin: 0;
	}

	p {
		margin-top: var(--space-1);
		color: var(--color-ink-muted);
	}

	.request-id {
		font-size: var(--font-size-xs);
	}

	button {
		min-height: 2.75rem;
		padding: var(--space-2) var(--space-4);
		border: var(--border-width) solid var(--color-primary);
		border-radius: var(--radius-sm);
		background: var(--color-primary-soft);
		color: var(--color-primary);
		cursor: pointer;
		font-weight: 700;
	}

	@media (max-width: 32rem) {
		.state {
			grid-template-columns: auto 1fr;
		}

		button {
			grid-column: 1 / -1;
		}
	}
</style>
