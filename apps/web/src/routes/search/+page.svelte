<script lang="ts">
	import { goto } from '$app/navigation';
	import { navigating } from '$app/state';
	import type { PageProps } from './$types';
	import type { SearchResponse, SearchResultRead } from '#lib/api/contracts.ts';
	import ActorDiscovery from '#lib/components/ActorDiscovery.svelte';
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
		// One-shot form serialization must not inherit reactive URL state.
		// eslint-disable-next-line svelte/prefer-svelte-reactivity
		const formParams = new URLSearchParams();
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
				<div>
					<p>Published intelligence</p>
					<h1 id="search-title">Research search</h1>
					<span>Find the actor and evidence behind an indicator, CVE, technique or campaign.</span>
				</div>
			</div>
			<div class="boundary-state">
				<div><small>Review status</small><strong>Published records</strong></div>
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
				<span>Search the intelligence index</span>
				<small>Reviewed public records only</small>
			</div>
			<div class="search-row">
				<label class="query-shell" for="search-query">
					<input
						id="search-query"
						aria-label="Search published intelligence"
						type="search"
						name="q"
						value={searchState.query}
						placeholder="indicator, CVE, actor, alias, technique…"
						minlength="2"
						maxlength="200"
						autocomplete="off"
						spellcheck="false"
					/>
				</label>
				<SearchFilters state={searchState} />
				<button class="search-button" type="submit">Search</button>
			</div>
			<div class="active-scope">
				<span
					>Types: {searchState.entityTypes.length
						? searchState.entityTypes.join(' + ')
						: 'all published intelligence'}</span
				>
				{#if searchState.intelligenceType}<span>Assessment: {searchState.intelligenceType}</span
					>{/if}
				{#if searchState.dateFrom || searchState.dateTo}<span
						>Dates: {searchState.dateFrom || 'earliest'} to {searchState.dateTo || 'latest'}</span
					>{/if}
				{#if hasFilters}<a
						href={searchState.query
							? `/search?q=${encodeURIComponent(searchState.query)}`
							: '/search'}>Clear filters</a
					>{/if}
			</div>
		</form>

		<div class="research-contract" aria-label="Search behavior">
			<div>
				<strong>Start with what you know</strong><small>Domains, IPs, URLs and hashes</small>
			</div>
			<div>
				<strong>Follow the vulnerability</strong><small>See CVEs in their actor context</small>
			</div>
			<div>
				<strong>Understand the adversary</strong><small
					>Identity, aliases and behavior included</small
				>
			</div>
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
				<div id="results-heading"><ActorDiscovery discovery={data.discovery} /></div>
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
						title={`No published matches for ${data.response?.query ?? searchState.query}`}
						message="Broaden the wording or remove a filter. Internal and unpublished records remain outside this interface."
					/>
				</div>
			{:else}
				<header class="results-header">
					<div>
						<p class="state-code">{results.length} published results for</p>
						<h2 id="results-heading">{data.response?.query ?? searchState.query}</h2>
					</div>
					<span class="publication-mark">Reviewed intelligence</span>
				</header>

				<div class="result-list">
					{#each results as result (result.id)}
						<SearchResultCard {result} fromSearch={searchUrl} query={searchState.query} />
					{/each}
				</div>

				{#if loadMoreError}
					<div class="load-error" role="alert">
						<div>
							<strong>Current results remain available</strong>
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
					</div>
				{:else}
					<p class="end-marker">You have reached the end of the published results.</p>
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
		background-image: radial-gradient(
			circle at 82% 8%,
			var(--color-primary-faint),
			transparent 28rem
		);
	}

	.search-workspace::before {
		position: absolute;
		inset: 0 0 auto;
		height: var(--border-width);
		background: var(--gradient-brand);
		content: '';
	}

	.workspace-inner {
		max-width: 76rem;
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	.intel-banner {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-6);
		padding-bottom: var(--space-7);
	}

	.title-lockup,
	.boundary-state,
	.stale-notice,
	.publication-mark {
		display: flex;
		align-items: center;
	}

	.title-lockup {
		gap: var(--space-5);
	}
	.title-lockup p,
	.state-code,
	.console-label,
	.active-scope,
	.publication-mark,
	.end-marker {
		font-size: var(--font-size-sm);
	}

	.title-lockup p,
	.state-code {
		margin: 0;
		color: var(--color-primary);
		font-weight: 700;
	}

	.title-lockup h1 {
		margin: var(--space-2) 0 var(--space-3);
		font-size: clamp(2.6rem, 5vw, 4.5rem);
		line-height: 1.02;
		letter-spacing: -0.035em;
	}

	.title-lockup > div > span {
		color: var(--color-ink-muted);
	}

	.boundary-state {
		gap: var(--space-3);
		padding: var(--space-3) var(--space-4);
		border: var(--border-width) solid var(--color-border);
		border-radius: 999px;
		background: var(--color-surface);
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
		color: var(--color-ink-subtle);
		font-size: var(--font-size-xs);
	}
	.boundary-state strong {
		font-size: var(--font-size-sm);
	}

	.search-console {
		padding: var(--space-5);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-lg);
		background: var(--color-surface);
		box-shadow: var(--shadow-panel);
	}

	.console-label,
	.active-scope {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		padding: 0;
		color: var(--color-ink);
	}

	.console-label span {
		font-size: var(--font-size-lg);
		font-weight: 750;
	}
	.console-label small {
		color: var(--color-ink-subtle);
	}

	.search-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto auto;
		gap: var(--space-3);
		padding: var(--space-4) 0;
	}

	.query-shell {
		display: flex;
		min-width: 0;
		min-height: 3rem;
		align-items: center;
		gap: var(--space-3);
		padding: 0 var(--space-4);
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-md);
		background: var(--color-canvas-soft);
	}

	.query-shell:focus-within {
		border-color: var(--color-focus);
		box-shadow: var(--shadow-focus);
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
		background: var(--color-primary);
		color: var(--color-canvas);
		cursor: pointer;
		font-weight: 750;
	}

	.search-button {
		min-height: 3rem;
		padding: 0 var(--space-5);
	}
	.search-button:hover,
	.load-more button:hover,
	.load-error button:hover {
		background: var(--color-focus);
		box-shadow: none;
	}

	.active-scope {
		justify-content: flex-start;
		flex-wrap: wrap;
		gap: var(--space-2);
		color: var(--color-ink-muted);
	}
	.active-scope span {
		padding: var(--space-1) var(--space-3);
		border: var(--border-width) solid var(--color-border);
		border-radius: 999px;
	}
	.active-scope a {
		margin-left: auto;
		color: var(--color-primary);
	}

	.research-contract {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: var(--space-5);
		margin-top: var(--space-6);
	}

	.research-contract div {
		display: grid;
		gap: var(--space-1);
		padding-left: var(--space-4);
		border-left: 0.1875rem solid var(--color-border-strong);
	}
	.research-contract div:first-child {
		border-left: 0;
	}
	.research-contract strong {
		color: var(--color-ink);
		font-size: var(--font-size-base);
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
		margin-top: var(--space-8);
	}
	.invalid-state {
		display: grid;
		grid-template-columns: 1fr;
		align-items: center;
		gap: var(--space-6);
		padding: clamp(2rem, 5vw, 3.5rem) 0;
		border-top: var(--border-width) solid var(--color-border-strong);
	}
	.invalid-state {
		border-top-color: var(--color-critical);
	}
	.invalid-state h2,
	.results-header h2 {
		margin: var(--space-2) 0;
		font-size: clamp(1.4rem, 4vw, 2.15rem);
	}
	.invalid-state ul {
		max-width: 48rem;
		margin-bottom: 0;
		color: var(--color-ink-muted);
	}

	.results-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--space-5);
		margin-bottom: var(--space-5);
		padding-bottom: var(--space-5);
		border-bottom: var(--border-width) solid var(--color-border-strong);
	}
	.publication-mark {
		padding: var(--space-2) var(--space-3);
		border-radius: 999px;
		background: var(--color-observed-soft);
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
			grid-template-columns: 1fr;
		}
		.research-contract div {
			padding-top: var(--space-4);
			padding-left: 0;
			border-top: var(--border-width) solid var(--color-border);
			border-left: 0;
		}
		.research-contract div:first-child {
			padding-top: 0;
			border-top: 0;
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
		.results-header,
		.load-error {
			align-items: flex-start;
			flex-direction: column;
		}
	}
</style>
