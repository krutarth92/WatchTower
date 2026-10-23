<script lang="ts">
	import type { SearchState } from '#lib/search/state.ts';
	import { searchEntityTypes } from '#lib/search/state.ts';

	let { state }: { state: SearchState } = $props();
	let dialog: HTMLDialogElement;

	function openFilters() {
		dialog.showModal();
		requestAnimationFrame(() => dialog.querySelector<HTMLInputElement>('input')?.focus());
	}

	const activeCount = $derived(
		state.entityTypes.length +
			Number(Boolean(state.intelligenceType)) +
			Number(Boolean(state.sourceId)) +
			Number(Boolean(state.dateFrom)) +
			Number(Boolean(state.dateTo))
	);
</script>

<button class="filter-trigger" type="button" onclick={openFilters}>
	<span aria-hidden="true">⌁</span> Filters
	{#if activeCount}<span class="count">{activeCount}</span>{/if}
</button>

<dialog bind:this={dialog} aria-labelledby="filter-title">
	<div class="dialog-bar">
		<div>
			<p>SEARCH SCOPE</p>
			<h2 id="filter-title">Filter published intelligence</h2>
		</div>
		<button class="close" type="button" aria-label="Close filters" onclick={() => dialog.close()}
			>×</button
		>
	</div>

	<div class="filter-body">
		<fieldset>
			<legend>Entity type</legend>
			<div class="entity-options">
				{#each searchEntityTypes as entityType (entityType)}
					<label>
						<input
							type="checkbox"
							name="entity_type"
							value={entityType}
							checked={state.entityTypes.includes(entityType)}
						/>
						<span>{entityType}</span>
					</label>
				{/each}
			</div>
		</fieldset>

		<label class="field">
			<span>Intelligence type</span>
			<select name="intelligence_type" value={state.intelligenceType}>
				<option value="">Any intelligence type</option>
				<option value="observed">Observed</option>
				<option value="assessed">Assessed</option>
			</select>
		</label>

		<label class="field full">
			<span>Source ID</span>
			<input
				type="text"
				name="source_id"
				value={state.sourceId}
				placeholder="UUID"
				spellcheck="false"
			/>
		</label>

		<label class="field">
			<span>From date <small>UTC</small></span>
			<input type="date" name="date_from" value={state.dateFrom} />
		</label>

		<label class="field">
			<span>To date <small>UTC</small></span>
			<input type="date" name="date_to" value={state.dateTo} />
		</label>
	</div>

	<div class="dialog-actions">
		<a href={state.query ? `/search?q=${encodeURIComponent(state.query)}` : '/search'}
			>Clear filters</a
		>
		<button type="submit">Apply filters</button>
	</div>
</dialog>

<style>
	.filter-trigger,
	.dialog-actions button,
	.close {
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-sm);
		background: var(--color-surface-raised);
		color: var(--color-ink);
		cursor: pointer;
	}

	.filter-trigger {
		display: inline-flex;
		min-height: 3rem;
		align-items: center;
		gap: var(--space-2);
		padding: 0 var(--space-4);
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
	}

	.filter-trigger:hover,
	.close:hover {
		border-color: var(--color-primary);
		color: var(--color-primary);
	}

	.count {
		display: grid;
		min-width: 1.35rem;
		height: 1.35rem;
		place-items: center;
		border-radius: 50%;
		background: var(--color-primary-soft);
		color: var(--color-primary);
		font-size: var(--font-size-xs);
		font-weight: 700;
	}

	dialog {
		width: min(42rem, calc(100% - 2rem));
		max-height: calc(100vh - 2rem);
		padding: 0;
		overflow: auto;
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-lg);
		background: var(--gradient-surface), var(--color-surface);
		color: var(--color-ink);
		box-shadow: var(--shadow-panel), var(--shadow-glow);
	}

	dialog::backdrop {
		background: var(--color-scrim);
		backdrop-filter: blur(var(--space-1));
	}

	.dialog-bar,
	.dialog-actions {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding: var(--space-4) var(--space-5);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.dialog-bar p,
	.field > span,
	legend {
		margin: 0;
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
	}

	.dialog-bar h2 {
		margin: var(--space-1) 0 0;
		font-size: var(--font-size-lg);
	}

	.close {
		width: 2.5rem;
		height: 2.5rem;
		font-size: var(--font-size-lg);
	}

	.filter-body {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-5);
		padding: var(--space-5);
	}

	fieldset,
	.full {
		grid-column: 1 / -1;
	}

	fieldset {
		margin: 0;
		padding: 0;
		border: 0;
	}

	legend {
		margin-bottom: var(--space-3);
	}

	.entity-options {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.entity-options label {
		position: relative;
	}

	.entity-options input {
		position: absolute;
		width: 1px;
		height: 1px;
		opacity: 0;
	}

	.entity-options span {
		display: block;
		padding: var(--space-2) var(--space-3);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-sm);
		color: var(--color-ink-muted);
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		text-transform: capitalize;
	}

	.entity-options input:checked + span {
		border-color: var(--color-primary);
		background: var(--color-primary-soft);
		color: var(--color-primary);
	}

	.entity-options input:focus-visible + span {
		outline: var(--border-width) solid var(--color-focus);
		outline-offset: var(--space-1);
		box-shadow: var(--shadow-focus);
	}

	.field {
		display: grid;
		gap: var(--space-2);
	}

	.field small {
		color: var(--color-ink-subtle);
	}

	.field input,
	.field select {
		width: 100%;
		min-height: 2.75rem;
		padding: var(--space-2) var(--space-3);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-canvas);
		color: var(--color-ink);
	}

	.dialog-actions {
		border-top: var(--border-width) solid var(--color-border);
		border-bottom: 0;
	}

	.dialog-actions a {
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}

	.dialog-actions button {
		min-height: 2.75rem;
		padding: 0 var(--space-5);
		border-color: var(--color-primary);
		background: var(--color-primary-soft);
		color: var(--color-primary);
		font-weight: 700;
	}

	@media (max-width: 40rem) {
		.filter-body {
			grid-template-columns: 1fr;
			padding: var(--space-4);
		}

		fieldset,
		.full {
			grid-column: auto;
		}
	}
</style>
