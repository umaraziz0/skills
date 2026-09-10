# Changelog

## [2.0.0](https://github.com/umaraziz0/skills/compare/v1.1.2...v2.0.0) (2026-09-10)


### ⚠ BREAKING CHANGES

* remove `dependabot-merge`
* sunset `generate-pr-description`, agents can directly create PR & use template

### Features

* create `cleanup-tests` skill ([8645504](https://github.com/umaraziz0/skills/commit/864550441c52b9a6fe891ccbf5bd0451b9b92ed8))
* create `dependabot-merge` skill ([c24927c](https://github.com/umaraziz0/skills/commit/c24927c114b1a1ed089a57335b534680cdfc2c30))
* create `pr-and-babysit` skill ([3403530](https://github.com/umaraziz0/skills/commit/34035308436b0051439b907528694a74daef3175))
* sunset `generate-pr-description`, agents can directly create PR & use template ([2961dfd](https://github.com/umaraziz0/skills/commit/2961dfddb70f70390fd17d5787f5cb9b044097f6))


### Bug Fixes

* **cleanup-tests:** remove `/tdd` dependency ([cbedded](https://github.com/umaraziz0/skills/commit/cbedded323a40998a05ad1cfa81f24e1a1aed172))
* **clenaup-tests:** add `next-step` attribute to unresolved findings ([af6f59b](https://github.com/umaraziz0/skills/commit/af6f59bdbe4b9c43a6864d0565b11259b98f82f5))
* **dependabot-merge:** lax invocation ([44fac72](https://github.com/umaraziz0/skills/commit/44fac72de72cd77cb6decbd3542ea6f4a08ca51b))
* **dependabot-merge:** optimize with guidelines ([7100225](https://github.com/umaraziz0/skills/commit/7100225dba0c83afa38327dfa6e19b64fdd40ef2))
* **generate-pr-description:** optimize skill against guidelines ([504e53a](https://github.com/umaraziz0/skills/commit/504e53a67ef0d4d1a2a82f96c457bb1d2c0e39a5))
* remove `dependabot-merge` ([0b438e7](https://github.com/umaraziz0/skills/commit/0b438e7e37d6a6804cc2ffc3a350889b18f384eb))
* **review-pr-breaking:** optimize skill against guidelines ([929a9b4](https://github.com/umaraziz0/skills/commit/929a9b4bca8113de451c623982fdf0f6178944f2))
* **ssh:** fix not allowing other `SSH_` prefixed envs ([aed1de1](https://github.com/umaraziz0/skills/commit/aed1de119192d2a561ec96d4e63ea206a5df7054))
* **ssh:** optimize with guidelines ([42999c0](https://github.com/umaraziz0/skills/commit/42999c0673e7fc5166d664afa24e5f7687cf212e))
* **tight-review:** fix output formatting ([c9156ea](https://github.com/umaraziz0/skills/commit/c9156ea926dc4d7e0387f040401a44dc010c5be5))
* **tight-review:** optimize skill with guidelines ([cd9eee0](https://github.com/umaraziz0/skills/commit/cd9eee0fa4942d5cbc0749d5b1e1812ada542927))
* **tight-review:** update to implementation-only ([26b36bb](https://github.com/umaraziz0/skills/commit/26b36bbcdf16b7dfa0814acc58cd8e3370bbb068))

## [1.1.2](https://github.com/umaraziz0/skills/compare/v1.1.1...v1.1.2) (2026-08-02)


### Bug Fixes

* **tight-review:** modify to be more lax ([2517c9c](https://github.com/umaraziz0/skills/commit/2517c9c61f62e32086090d4d64b66f93a0d07937))

## [1.1.1](https://github.com/umaraziz0/skills/compare/v1.1.0...v1.1.1) (2026-07-30)


### Bug Fixes

* **ssh:** remove environment feature ([1d36f55](https://github.com/umaraziz0/skills/commit/1d36f551d28fa99056857cb630e19172d611a773))

## [1.1.0](https://github.com/umaraziz0/skills/compare/v1.0.0...v1.1.0) (2026-07-25)


### Features

* add `tight-review` skill ([107f487](https://github.com/umaraziz0/skills/commit/107f487da666691bbe41cc5e6e79c37db3b98778))
* **tight-review:** add modes ([cc69574](https://github.com/umaraziz0/skills/commit/cc69574c3afdae8d09e276e7388a7687ed657dcf))
* **tight-review:** add subtypes ([04096ad](https://github.com/umaraziz0/skills/commit/04096adb63193735eb635cce78cdcf0dde75e237))

## 1.0.0 (2026-07-18)


### ⚠ BREAKING CHANGES

* reset skills

### Features

* rewrite `generate-pr-description` ([61fb34e](https://github.com/umaraziz0/skills/commit/61fb34e2a029da74411bb2a1cd028b2ff20482df))
* setup repo for skills.sh install ([2cd7ee3](https://github.com/umaraziz0/skills/commit/2cd7ee317acea08b31742b198c73d23cc8a49496))
* setup skills ([9937c3e](https://github.com/umaraziz0/skills/commit/9937c3e027a69ee2799ba8125dfbc06933a3a1fb))
* **ssh:** add environment context support ([1c72a38](https://github.com/umaraziz0/skills/commit/1c72a3833bc6360ec727858dd84cb67205bc38bc))


### Bug Fixes

* fix template path on `generate-pr-description` ([51bb1bd](https://github.com/umaraziz0/skills/commit/51bb1bded2db18a70b0131052a4177c422483da6))
* make skills more project-agnostic ([5d3aa35](https://github.com/umaraziz0/skills/commit/5d3aa3504a90c20bb16ee39d8c11f23a95a28727))
* reset skills ([37f0de4](https://github.com/umaraziz0/skills/commit/37f0de49f495fdde82ccab8d79e023cb3e295417))
* rewrite `review-pr-breaking` ([a25bd91](https://github.com/umaraziz0/skills/commit/a25bd914e844894728916e8c99c3d20c47ee8eea))
* rewrite `ssh` ([4a7d87b](https://github.com/umaraziz0/skills/commit/4a7d87bcc2958063cb4e77c17783bcc01124c41c))
* **ssh:** fix environment context ([6249842](https://github.com/umaraziz0/skills/commit/6249842da522deb36fc86bcb09d9de8f8a95edda))
* **ssh:** fix flow ([b0eb701](https://github.com/umaraziz0/skills/commit/b0eb701671a42e5cd9d1f8c7fc3ee453ddb06231))
* **ssh:** fix ssh skill flow ([b213a09](https://github.com/umaraziz0/skills/commit/b213a09b128d6b7849133c48413478e05d3492b3))
* **ssh:** optimize skill file ([b832c8e](https://github.com/umaraziz0/skills/commit/b832c8ecd633b270fc91e5bf1a0597c0420604ae))
* **ssh:** update security ([a1636f0](https://github.com/umaraziz0/skills/commit/a1636f0eb2af71dbfc85716036bbc9936e25c562))
* trim `review-pr-breaking` ([376f0d0](https://github.com/umaraziz0/skills/commit/376f0d0ae8724c57b3db2066942d821027348dfd))
* update `review-pr-breaking` to consider queue workers ([0c37b73](https://github.com/umaraziz0/skills/commit/0c37b73658b4f1075c33a0728b49963e29b89b3e))

## Changelog
