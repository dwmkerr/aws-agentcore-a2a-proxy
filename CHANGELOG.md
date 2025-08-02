# Changelog

## [0.2.0](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/compare/v0.1.4...v0.2.0) (2025-08-02)


### Features

* add clear warning when AWS credentials are missing ([dee6fc5](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/dee6fc56e1f9528a4f3fb5e21be4c0305e3075f1))
* add GitHub Development Assistant agent with OIDC integration ([6bcde02](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/6bcde02deb6d3e69d73f6ed8ca5ad13d3c23b314))
* implement proper OIDC authentication with GitHub token extraction ([831e875](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/831e875e5931d43817430550406bce47c3318cf5))
* update GitHub agent to use GitHub's hosted MCP server ([79dad8a](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/79dad8a483a3dd0619ac76f12a1bf70ddf74077b))


### Bug Fixes

* add colored WARNING logging and improve message ([70fce9f](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/70fce9fbb9780aab22796b26e50d499298a7967f))
* gracefully handle AWS connection failures during startup ([2ef95e2](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/2ef95e2eb7ddb72d9b1c3d01551c2a7246352636))
* resolve A2A inspector validation errors and add request logging ([6123c59](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/6123c598450b434f68eee1300fa64a562cecd4fa))
* shorten warning message for better UX ([00cda08](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/00cda08c4629f077ca76cacde5ddeef0c09aeb54))
* simplify Makefile dev command to use hardcoded localhost ([c5172bf](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/c5172bf1af4d522c1c6a95e15621a34d1f1b2f01))
* use localhost instead of 0.0.0.0 for development server ([7294faf](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/7294fafb11b0a2b206c4a074e1a48d3c126c70bd))


### Documentation

* add PyPI and Codecov badges to README ([05406c7](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/05406c71ec33d46c58ac2879e33f7b0157c2175b))
* clean up README by removing unnecessary sections ([238578d](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/238578d9659f54275246ec7871ca6ca8eec6c46c))
* document AWS credential chain and development without AWS ([521202a](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/521202a4e1cbcb9bc2607f3c3d473772dcd1f376))
* update README with AWS operator agent section and remove customer support demo ([38a7997](https://github.com/dwmkerr/aws-bedrock-a2a-proxy/commit/38a7997f336c5fed3fb08c230568fe122d6ff613))
