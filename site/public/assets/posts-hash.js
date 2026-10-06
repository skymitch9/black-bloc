export const SECTION_HASHES = ['sect-the-posts', 'sect-blocks', 'sect-sticky', 'sect-machinery'];

/** The post a Posts-page hash names, or null when it names a section of the page or nothing. */
export function postSlugOf(hash) {
  const wanted = String(hash || '').replace(/^#/, '').trim();
  return wanted && !SECTION_HASHES.includes(wanted) ? wanted : null;
}
