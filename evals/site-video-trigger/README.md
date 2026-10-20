# site-video trigger eval

Five requests in everyday phrasing must load `site-video` ("make a video", "scroll through the website", "zoom in",
"Screen Studio", "video editing", a video that looks jumpy or compressed after upload); four near-misses must not (a
carousel, editing a graphic, a website animation, a screen recording the person makes). Run from the repository root
with a Claude Code that has `plugin eval` (2.1.269 or later):

    claude plugin eval plugins/site-video --eval-dir evals/site-video-trigger --runs 1 --ablation none --no-publish --trust-plugin

Results are written outside the plugin with `--output-dir`; they are not part of the plugin.
