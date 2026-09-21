/**
 * Where a run of blocks breaks into two columns. Document order is kept: the
 * first `columnSplit(heights)` blocks are the left column and the rest are the
 * right one, so a page's main list can never be demoted below its machinery.
 * Pure on purpose — site/mock/layout.test.mjs is the only other caller.
 */
export function columnSplit(heights) {
  if (heights.length < 2) return heights.length;
  const total = heights.reduce((sum, one) => sum + one, 0);
  let best = 1;
  let gap = Infinity;
  let left = 0;
  for (let at = 1; at < heights.length; at += 1) {
    left += heights[at - 1];
    const found = Math.abs(left - (total - left));
    if (found < gap) {
      gap = found;
      best = at;
    }
  }
  return best;
}
