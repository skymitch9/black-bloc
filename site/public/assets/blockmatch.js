// Pure matcher for the Blocks section's search box and filter chips — kept out of
// page-posts.js so it can be proved without a browser (site/mock/blockmatch.test.mjs).

export const BLOCK_FILTERS = [
  ['all', 'All', null],
  ['on_post', 'On a post', (kind) => (kind.on || []).length > 0],
  ['no_post', 'On no post', (kind) => (kind.on || []).length === 0],
  ['exclusive', 'One at a time', (kind) => Boolean(kind.exclusive)],
];

function haystack(kind) {
  return [kind.name, kind.where, ...(kind.keys || []).map((key) => key.replace(/_/g, ' '))]
    .join(' ')
    .toLowerCase();
}

/** query is expected already lowercased (searchField's own convention). */
export function blockMatches(kind, query, filterKey) {
  const rule = (BLOCK_FILTERS.find(([key]) => key === filterKey) || BLOCK_FILTERS[0])[2];
  const passesFilter = rule === null || rule(kind);
  const passesQuery = !query || haystack(kind).includes(query);
  return passesFilter && passesQuery;
}
