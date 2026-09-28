import { discordMock } from './ui.js';

// The one preview of a message that carries blocks: the post drawer, a version, each card in the
// Blocks section and every block editor draw through here. The bot draws each block with its
// own feature's code (black_bloc/preview.py:BLOCK_DRAWS); see code-notes.
const POST_FEATURE = 'post';

const listOf = (value) => (typeof value === 'function' ? value() : value) || [];

/**
 * `post` (a function answering {style, title, body}) draws the post with its `blocks` under it;
 * no `post` draws the blocks alone, as the Blocks section shows them. `feature` + `draft` is an
 * editor: the kind's own renderer, with the unsaved words laid over the saved ones.
 */
export function blockPreview({
  blocks = [],
  post = null,
  feature = null,
  draft = null,
  sample = () => ({}),
  always = false,
  lazy = false,
  say = null,
} = {}) {
  if (feature) {
    return discordMock({ feature, draft: draft || (() => ({})), sample, lazy, say });
  }
  return discordMock({
    feature: POST_FEATURE,
    lazy,
    say,
    sample: () => ({
      ...(post ? post() : { style: 'plain', title: '', body: '' }),
      blocks: listOf(blocks).join(','),
      always: always ? 'true' : '',
      ...(sample() || {}),
    }),
  });
}
