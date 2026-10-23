<script lang="ts">
	import { goto } from '$app/navigation';
	import { navigating } from '$app/state';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import type { PageProps } from './$types';
	import type { SearchResponse, SearchResultRead } from '#lib/api/contracts.ts';
	import SearchFilters from '#lib/components/SearchFilters.svelte';
	import SearchResultCard from '#lib/components/SearchResultCard.svelte';
	import StatePanel from '#lib/components/StatePanel.svelte';
	import { parseSearchState, serializeSearchState } from '#lib/search/state.ts';

	let { data }: PageProps = $props();
	let results = $state<SearchResultRead[]>([]);
	let nextCursor = $state<string | null>(null);
	let loadingMore = $state(false);
	let loadMoreError = $state<{ message: string; requestId: string | null } | null>(null);

	const searchState = $derived(data.search.state);
	const serialized = $derived(serializeSearchState(searchState).toString());
	const searchUrl = $derived(`/search${serialized ? `?${serialized}` : ''}`);
	const isNavigating = $derived(Boolean(navigating.to));
	const hasFilters = $derived(
		searchState.entityTypes.length > 0 ||
			Boolean(
				searchState.intelligenceType ||
				searchState.sourceId ||
				searchState.dateFrom ||
				searchState.dateTo
			)
	);

	$effect(() => {
		results = data.response?.data ? [...data.response.data] : [];
		nextCursor = data.response?.next_cursor ?? null;
		loadingMore = false;
		loadMoreError = null;
	});

	async function loadMore() {
		if (!nextCursor || loadingMore) return;
		loadingMore = true;
		loadMoreError = null;
		try {
			const response = await fetch(`/search/more?${serialized}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
				body: JSON.stringify({ cursor: nextCursor })
			});
			const body = (await response.json()) as
				| SearchResponse
				| { error: { message: string; requestId: string | null } };
			if (!response.ok || 'error' in body) {
				loadMoreError =
					'error' in body
						? body.error
						: { message: 'More published intelligence could not be loaded.', requestId: null };
				return;
			}
			results = [...results, ...body.data];
			nextCursor = body.next_cursor;
		} catch {
			loadMoreError = {
				message: 'More published intelligence could not be loaded.',
				requestId: null
			};
		} finally {
			loadingMore = false;
		}
	}

	function retryPage() {
		window.location.reload();
	}

	function submitSearch(event: SubmitEvent) {
		event.preventDefault();
		const form = event.currentTarget as HTMLFormElement;
		const formParams = new SvelteURLSearchParams();
		for (const [key, value] of new FormData(form)) {
			if (typeof value === 'string' && value.trim()) formParams.append(key, value);
		}
		const next = serializeSearchState(parseSearchState(formParams).state).toString();
		form.querySelector<HTMLDialogElement>('dialog[open]')?.close();
		void goto(`/search${next ? `?${next}` : ''}`);
	}
</script>

<svelte:head>
	<title>Published intelligence search | WATCHTOWER</title>
	<meta
		name="description"
		content="Search published adversary intelligence with explicit provenance and evidence labels."
	/>
</svelte:head>

<section class="search-workspace" aria-labelledby="search-title">
	<div class="workspace-inner">
		<header class="intel-banner">
			<div class="title-lockup">
				<div class="scope-mark" aria-hidden="true"><span></span></div>
				<div>
					<p>PUBLISHED INTELLIGENCE INDEX</p>
					<h1 id="search-title">Research search</h1>
					<span>Deterministic discovery across reviewed adversary intelligence</span>
				</div>
			</div>
			<div class="boundary-state">
				<span class="signal" aria-hidden="true"></span>
				<div><small>VISIBILITY BOUNDARY</small><strong>PUBLISHED ONLY</strong></div>
			</div>
		</header>

		<form
			class="search-console"
			method="GET"
			action="/search"
			onsubmit={submitSearch}
			aria-label="Published intelligence search"
		>
			<div class="console-label">
				<span>QUERY CONSOLE</span>
				<small>MIN 2 CHARACTERS / MAX 200</small>
			</div>
			<div class="search-row">
				<label class="query-shell" for="search-query">
					<span class="prompt" aria-hidden="true">WT://</span>
					<input
						id="search-query"
						aria-label="Search published intelligence"
						type="search"
						name="q"
						value={searchState.query}
						placeholder="actor, alias, technique, behavior, observation…"
						minlength="2"
						maxlength="200"
						autocomplete="off"
						spellcheck="false"
					/>
				</label>
				<SearchFilters state={searchState} />
				<button class="search-button" type="submit"
					><span aria-hidden="true">⌕</span> Run search</button
				>
			</div>
			<div class="active-scope">
				<span
					>ENTITY: {searchState.entityTypes.length
						? searchState.entityTypes.join(' + ')
						: 'ALL'}</span
				>
				<span>INTEL: {searchState.intelligenceType || 'ANY'}</span>
				<span>WINDOW: {searchState.dateFrom || 'OPEN'} → {searchState.dateTo || 'OPEN'}</span>
				{#if hasFilters}<a
						href={searchState.query
							? `/search?q=${encodeURIComponent(searchState.query)}`
							: '/search'}>RESET SCOPE</a
					>{/if}
			</div>
		</form>

		<div class="research-contract" aria-label="Search behavior">
			<div><span>01</span><strong>API ORDER</strong><small>No local reranking</small></div>
			<div><span>02</span><strong>EXPLICIT TYPE</strong><small>Observed or assessed</small></div>
			<div><span>03</span><strong>SOURCE CONTEXT</strong><small>References preserved</small></div>
			<div><span>04</span><strong>BOUNDED PAGE</strong><small>25 records per request</small></div>
		</div>

		{#if isNavigating && results.length}
			<div class="stale-notice" role="status">
				<span class="signal" aria-hidden="true"></span>
				Updating scope. Current records remain visible and may be stale.
			</div>
		{/if}

		<section
			class="result-surface"
			aria-labelledby="results-heading"
			aria-busy={isNavigating || loadingMore}
		>
			{#if isNavigating && !results.length}
				<StatePanel
					state="loading"
					title="Running published search"
					message="Applying the current query and scope."
				/>
			{:else if data.view === 'initial'}
				<div class="initial-state">
					<div class="scan-mark" aria-hidden="true"><span></span><span></span><span></span></div>
					<div>
						<p class="state-code">INDEX READY / NO QUERY</p>
						<h2 id="results-heading">Enter a signal to begin</h2>
						<p>
							Use an actor name, source alias, MITRE technique such as <code>T1059.001</code>, or
							words from an observed behavior. Only published records are returned.
						</p>
					</div>
				</div>
			{:else if data.view === 'invalid'}
				<div class="invalid-state" role="alert">
					<p class="state-code">REQUEST REJECTED / LOCAL VALIDATION</p>
					<h2 id="results-heading">Correct the query scope</h2>
					<ul>
						{#each data.search.errors as error (error)}<li>{error}</li>{/each}
					</ul>
				</div>
			{:else if data.view === 'unavailable'}
				<div id="results-heading">
					<StatePanel
						state="error"
						title={data.error?.status === 429 ? 'Search rate limited' : 'Search unavailable'}
						message={data.error?.message ?? 'Published intelligence search is unavailable.'}
						requestId={data.error?.requestId ?? undefined}
						onRetry={retryPage}
					/>
				</div>
			{:else if data.view === 'empty'}
				<div id="results-heading">
					<StatePanel
						state="empty"
						title={`No published matches for “${data.response?.query ?? searchState.query}”`}
						message="Broaden the wording or remove a filter. Internal and unpublished records remain outside this interface."
					/>
				</div>
			{:else}
				<header class="results-header">
					<div>
						<p class="state-code">QUERY COMPLETE / {results.length} RECORDS LOADED</p>
						<h2 id="results-heading">“{data.response?.query ?? searchState.query}”</h2>
					</div>
					<span class="publication-mark"
						><span class="signal" aria-hidden="true"></span> PUBLICATION FILTERED</span
					>
				</header>

				<div class="result-list">
					{#each results as result (result.id)}
						<SearchResultCard {result} fromSearch={searchUrl} />
					{/each}
				</div>

				{#if loadMoreError}
					<div class="load-error" role="alert">
						<div>
							<strong>CURRENT RECORDS RETAINED</strong>
							<span>{loadMoreError.message}</span>
							{#if loadMoreError.requestId}<code>REQUEST {loadMoreError.requestId}</code>{/if}
						</div>
						<button type="button" onclick={loadMore}>Retry page</button>
					</div>
				{/if}

				{#if nextCursor}
					<div class="load-more">
						<button type="button" onclick={loadMore} disabled={loadingMore}>
							{loadingMore ? 'Loading next page…' : 'Load more results'}
						</button>
						<span>APPENDS IN BACKEND RELEVANCE ORDER</span>
					</div>
				{:else}
					<p class="end-marker">— END OF PUBLISHED RESULTS —</p>
				{/if}
			{/if}
		</section>
	</div>
</section>

<style>
	.search-workspace {
		position: relative;
		min-height: calc(100vh - var(--header-height));
		background-color: var(--color-canvas);
		background-image: var(--gradient-ambient), var(--texture-grid);
		background-size:
			auto,
			var(--grid-size) var(--grid-size);
	}

	.search-workspace::before {
		position: absolute;
		inset: 0 0 auto;
		height: var(--border-width);
		background: var(--gradient-brand);
		content: '';
	}

	.workspace-inner {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: var(--space-7) var(--space-5) var(--space-8);
	}

	.intel-banner {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-6);
		padding-bottom: var(--space-6);
	}

	.title-lockup,
	.boundary-state,
	.stale-notice,
	.publication-mark {
		display: flex;
		align-items: center;
	}

	.title-lockup {
		gap: var(--space-4);
	}
	.title-lockup p,
	.state-code,
	.console-label,
	.active-scope,
	.publication-mark,
	.end-marker,
	.load-more span {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	.title-lockup p,
	.state-code {
		margin: 0;
		color: var(--color-primary);
		font-weight: 700;
	}

	.title-lockup h1 {
		margin: var(--space-1) 0;
		font-size: clamp(1.8rem, 4vw, 3rem);
		line-height: 1;
		letter-spacing: -0.035em;
	}

	.title-lockup > div > span {
		color: var(--color-ink-muted);
	}

	.scope-mark {
		position: relative;
		display: grid;
		width: 4rem;
		height: 4rem;
		place-items: center;
		transform: rotate(45deg);
		box-shadow: 0 0 var(--space-5) var(--color-primary-glow);
	}

	.scope-mark::before,
	.scope-mark::after,
	.scope-mark span {
		position: absolute;
		background: var(--color-primary);
		content: '';
	}

	.scope-mark::before {
		width: 60%;
		height: var(--border-width);
	}
	.scope-mark::after {
		width: var(--border-width);
		height: 60%;
	}
	.scope-mark span {
		width: var(--space-2);
		height: var(--space-2);
		border-radius: 50%;
		box-shadow: 0 0 var(--space-3) currentColor;
	}

	.boundary-state {
		gap: var(--space-3);
		padding: var(--space-2) 0;
		color: var(--color-observed);
	}

	.signal {
		flex: none;
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: currentColor;
		box-shadow: 0 0 var(--space-3) currentColor;
	}

	.boundary-state div {
		display: grid;
	}
	.boundary-state small {
		font-family: var(--font-mono);
		font-size: 0.625rem;
		letter-spacing: var(--letter-spacing-label);
	}
	.boundary-state strong {
		font-size: var(--font-size-sm);
	}

	.search-console {
		margin-top: var(--space-5);
		padding-block: var(--space-3);
		border-top: var(--border-width) solid var(--color-primary);
		border-bottom: var(--border-width) solid var(--color-border-strong);
	}

	.console-label,
	.active-scope {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		padding: var(--space-2) 0;
		color: var(--color-primary);
	}

	.console-label span {
		font-weight: 700;
	}
	.console-label small {
		color: var(--color-ink-subtle);
	}

	.search-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto auto;
		gap: var(--space-3);
		padding: var(--space-2) 0 var(--space-3);
	}

	.query-shell {
		display: flex;
		min-width: 0;
		min-height: 3rem;
		align-items: center;
		gap: var(--space-3);
		padding: 0 var(--space-1);
		border-bottom: var(--border-width) solid var(--color-border-strong);
	}

	.query-shell:focus-within {
		border-color: var(--color-focus);
		box-shadow: 0 var(--space-1) var(--space-3) calc(-1 * var(--space-2)) var(--color-primary-glow);
	}
	.prompt {
		color: var(--color-secondary);
		font-family: var(--font-mono);
		font-size: var(--font-size-sm);
		font-weight: 700;
	}
	.query-shell input {
		width: 100%;
		min-width: 0;
		border: 0;
		outline: 0;
		background: transparent;
		color: var(--color-ink);
	}
	.query-shell input::placeholder {
		color: var(--color-ink-subtle);
	}

	.search-button,
	.load-more button,
	.load-error button {
		border: var(--border-width) solid var(--color-primary);
		border-radius: var(--radius-sm);
		background: var(--color-primary-soft);
		color: var(--color-primary);
		cursor: pointer;
		font-family: var(--font-mono);
		font-weight: 750;
		text-transform: uppercase;
	}

	.search-button {
		min-height: 3rem;
		padding: 0 var(--space-5);
	}
	.search-button:hover,
	.load-more button:hover,
	.load-error button:hover {
		background: var(--color-primary-faint);
		box-shadow: 0 0 var(--space-4) var(--color-primary-glow);
	}

	.active-scope {
		justify-content: flex-start;
		flex-wrap: wrap;
		color: var(--color-ink-subtle);
	}
	.active-scope span {
		padding-right: var(--space-3);
		border-right: var(--border-width) solid var(--color-border);
	}
	.active-scope a {
		margin-left: auto;
		color: var(--color-primary);
	}

	.research-contract {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		margin-top: var(--space-4);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.research-contract div {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0 var(--space-3);
		padding: var(--space-3) var(--space-4) var(--space-3) 0;
	}
	.research-contract div:first-child {
		border-left: 0;
	}
	.research-contract span {
		grid-row: 1 / 3;
		color: var(--color-secondary);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
	}
	.research-contract strong {
		color: var(--color-ink);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}
	.research-contract small {
		color: var(--color-ink-subtle);
	}

	.stale-notice {
		gap: var(--space-3);
		margin-top: var(--space-4);
		padding: var(--space-3) var(--space-4);
		border-left: 0.1875rem solid var(--color-assessed);
		color: var(--color-assessed);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
	}

	.result-surface {
		margin-top: var(--space-6);
	}
	.initial-state,
	.invalid-state {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: center;
		gap: var(--space-6);
		padding: clamp(2rem, 5vw, 3.5rem) 0;
		border-top: var(--border-width) solid var(--color-border-strong);
	}
	.invalid-state {
		grid-template-columns: 1fr;
		border-top-color: var(--color-critical);
	}
	.initial-state h2,
	.invalid-state h2,
	.results-header h2 {
		margin: var(--space-2) 0;
		font-size: clamp(1.4rem, 4vw, 2.15rem);
	}
	.initial-state p:last-child,
	.invalid-state ul {
		max-width: 48rem;
		margin-bottom: 0;
		color: var(--color-ink-muted);
	}

	.scan-mark {
		position: relative;
		display: grid;
		width: 7rem;
		height: 7rem;
		place-items: center;
		border: var(--border-width) solid var(--color-primary);
		border-radius: 50%;
		box-shadow: inset 0 0 var(--space-6) var(--color-primary-faint);
	}
	.scan-mark::before,
	.scan-mark::after {
		position: absolute;
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: 50%;
		content: '';
	}
	.scan-mark::before {
		width: 68%;
		height: 68%;
	}
	.scan-mark::after {
		width: 32%;
		height: 32%;
	}
	.scan-mark span:first-child {
		width: var(--space-2);
		height: var(--space-2);
		border-radius: 50%;
		background: var(--color-primary);
		box-shadow: 0 0 var(--space-3) currentColor;
	}
	.scan-mark span:nth-child(2),
	.scan-mark span:last-child {
		position: absolute;
		background: var(--color-border-strong);
	}
	.scan-mark span:nth-child(2) {
		width: 80%;
		height: var(--border-width);
	}
	.scan-mark span:last-child {
		width: var(--border-width);
		height: 80%;
	}

	.results-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--space-5);
		margin-bottom: var(--space-4);
		padding-bottom: var(--space-3);
		border-bottom: var(--border-width) solid var(--color-border-strong);
	}
	.publication-mark {
		gap: var(--space-2);
		color: var(--color-observed);
		font-weight: 700;
	}
	.result-list {
		display: grid;
		gap: var(--space-3);
	}

	.load-more {
		display: grid;
		place-items: center;
		gap: var(--space-2);
		padding-top: var(--space-6);
	}
	.load-more button {
		min-width: min(100%, 18rem);
		min-height: 3rem;
		padding: 0 var(--space-5);
	}
	.load-more button:disabled {
		cursor: wait;
		opacity: 0.7;
	}
	.load-more span,
	.end-marker {
		color: var(--color-ink-subtle);
	}

	.load-error {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		margin-top: var(--space-4);
		padding: var(--space-4);
		border: var(--border-width) solid var(--color-critical);
		border-radius: var(--radius-sm);
		background: var(--color-surface-glass);
	}
	.load-error div {
		display: grid;
		gap: var(--space-1);
	}
	.load-error strong {
		color: var(--color-critical);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}
	.load-error span {
		color: var(--color-ink-muted);
	}
	.load-error code {
		color: var(--color-ink-subtle);
	}
	.load-error button {
		min-height: 2.5rem;
		padding: 0 var(--space-4);
	}
	.end-marker {
		margin: var(--space-6) 0 0;
		text-align: center;
	}

	@media (max-width: 58rem) {
		.research-contract {
			grid-template-columns: repeat(2, 1fr);
		}
		.research-contract div:nth-child(3) {
			border-left: 0;
			border-top: var(--border-width) solid var(--color-border);
		}
		.research-contract div:nth-child(4) {
			border-top: var(--border-width) solid var(--color-border);
		}
		.search-row {
			grid-template-columns: minmax(0, 1fr) auto;
		}
		.search-button {
			grid-column: 1 / -1;
		}
	}

	@media (max-width: 40rem) {
		.workspace-inner {
			padding: var(--space-6) var(--space-4) var(--space-8);
		}
		.intel-banner {
			align-items: flex-start;
			flex-direction: column;
		}
		.scope-mark {
			width: 3rem;
			height: 3rem;
		}
		.boundary-state {
			width: 100%;
		}
		.console-label {
			align-items: flex-start;
			flex-direction: column;
		}
		.search-row {
			grid-template-columns: 1fr;
		}
		.search-button {
			grid-column: auto;
		}
		.active-scope span {
			width: 100%;
			padding-right: 0;
			border-right: 0;
		}
		.active-scope a {
			margin-left: 0;
		}
		.research-contract {
			grid-template-columns: 1fr;
		}
		.research-contract div,
		.research-contract div:nth-child(4) {
			border-top: var(--border-width) solid var(--color-border);
			border-left: 0;
		}
		.research-contract div:first-child {
			border-top: 0;
		}
		.initial-state {
			grid-template-columns: 1fr;
			padding: var(--space-5);
		}
		.scan-mark {
			width: 5rem;
			height: 5rem;
		}
		.results-header,
		.load-error {
			align-items: flex-start;
			flex-direction: column;
		}
	}
</style>
